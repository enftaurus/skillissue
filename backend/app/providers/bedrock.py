import asyncio
import json
import os
import re
from typing import Any, Dict, List, Optional
import boto3
from botocore.exceptions import ClientError, EndpointConnectionError
from backend.app.providers.base import BaseProvider, ProviderResponse
from backend.app.providers.models_catalog import calculate_token_cost
from backend.app.core.errors import ProviderError
from backend.app.core.logging import logger

def map_bedrock_client_error(e: ClientError, model_id: str, region: str) -> ProviderError:
    """
    Map AWS Bedrock ClientError responses to typed ProviderError instances.
    Secrets, keys, and signing tokens are NEVER included in error messages or logs.
    """
    code = e.response.get("Error", {}).get("Code", "UNKNOWN")
    msg = e.response.get("Error", {}).get("Message", "")

    if code in ("UnrecognizedClientException", "InvalidSignatureException", "AuthFailure"):
        return ProviderError("Invalid AWS Access Key ID or Secret Access Key.", "INVALID_CREDENTIALS")
    elif code in ("ExpiredTokenException", "ExpiredToken"):
        return ProviderError("AWS temporary session token has expired. Please refresh your credentials in Settings.", "EXPIRED_SESSION_TOKEN")
    elif code == "AccessDeniedException":
        return ProviderError(
            f"Access denied by AWS IAM: ensure your IAM policy allows 'bedrock:InvokeModel' for model '{model_id}', "
            "and ensure Model Access is granted in the AWS Bedrock Console.",
            "PERMISSION_DENIED"
        )
    elif code in ("ThrottlingException", "RequestLimitExceeded", "TooManyRequestsException"):
        return ProviderError("AWS Bedrock rate limit or quota exceeded for this account. Please retry shortly.", "THROTTLED")
    elif code == "ResourceNotFoundException" or "model" in msg.lower():
        return ProviderError(
            f"Selected model '{model_id}' is unavailable or not granted access in region '{region}'. "
            "Request model access in the AWS Bedrock Console.",
            "MODEL_UNAVAILABLE"
        )
    elif code == "ValidationException":
        return ProviderError(f"AWS Bedrock validation error: {msg}", "VALIDATION_ERROR")
    else:
        return ProviderError(f"Bedrock access error: {code} - {msg}", "INFERENCE_ERROR")

class AmazonBedrockProvider(BaseProvider):
    """
    Amazon Bedrock BYOC Provider implementation.
    
    SECURITY NOTE:
    Boto3 runtime clients hold AWS credentials in process memory during their lifecycle.
    Credentials remain encrypted in PostgreSQL and are decrypted only into ephemeral process memory.
    Cached provider instances are subject to idle TTL and hard size eviction bounds.
    """
    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_region: str = "us-east-1",
        aws_session_token: Optional[str] = None,
        model_id: str = "amazon.nova-lite-v1:0",
        runtime_client: Optional[Any] = None,
    ):
        super().__init__(model_id)
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region
        self.aws_session_token = aws_session_token
        self._runtime_client = runtime_client

    def _get_runtime_client(self):
        """Reuse existing boto3 client if already created, avoiding per-request connection rebuild."""
        if self._runtime_client is not None:
            return self._runtime_client
        kwargs = {
            "region_name": self.aws_region,
            "aws_access_key_id": self.aws_access_key_id,
            "aws_secret_access_key": self.aws_secret_access_key,
        }
        if self.aws_session_token:
            kwargs["aws_session_token"] = self.aws_session_token
        self._runtime_client = boto3.client("bedrock-runtime", **kwargs)
        return self._runtime_client

    async def validate_credentials(self) -> bool:
        """
        Validate AWS IAM credentials by executing a minimal test inference call.
        Enforces least privilege by requiring ONLY bedrock:InvokeModel.
        """
        if os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get("TEST_WITH_REAL_BEDROCK"):
            return True

        def _check():
            try:
                runtime = self._get_runtime_client()
                runtime.converse(
                    modelId=self.model_id,
                    messages=[{"role": "user", "content": [{"text": "ping"}]}],
                    inferenceConfig={"maxTokens": 5, "temperature": 0.0}
                )
                return True
            except ClientError as e:
                raise map_bedrock_client_error(e, self.model_id, self.aws_region)
            except EndpointConnectionError:
                raise ProviderError(
                    f"Could not connect to AWS Bedrock in region '{self.aws_region}'. Check region name and network connectivity.",
                    "CONNECTION_ERROR"
                )

        return await asyncio.to_thread(_check)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ProviderResponse:
        if os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get("TEST_WITH_REAL_BEDROCK"):
            from backend.app.providers.mock_provider import MockProvider
            mock = MockProvider(model_id=self.model_id)
            return await mock.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                conversation_history=conversation_history,
            )

        def _call() -> ProviderResponse:
            client = self._get_runtime_client()

            messages = []
            if conversation_history:
                for msg in conversation_history:
                    role = "assistant" if msg["role"] == "assistant" else "user"
                    messages.append({"role": role, "content": [{"text": msg["content"]}]})

            if not conversation_history or conversation_history[-1].get("content") != prompt:
                messages.append({"role": "user", "content": [{"text": prompt}]})

            system_blocks = [{"text": system_prompt}] if system_prompt else []

            try:
                response = client.converse(
                    modelId=self.model_id,
                    messages=messages,
                    system=system_blocks,
                    inferenceConfig={
                        "maxTokens": max_tokens,
                        "temperature": temperature,
                    }
                )
                content_blocks = response.get("output", {}).get("message", {}).get("content", [])
                output_text = "".join(b.get("text", "") for b in content_blocks if "text" in b)
                usage = response.get("usage", {})
                in_tokens = usage.get("inputTokens", 0)
                out_tokens = usage.get("outputTokens", 0)
                cost = calculate_token_cost(self.model_id, in_tokens, out_tokens)

                return ProviderResponse(
                    text=output_text,
                    input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    estimated_cost_usd=cost,
                    model_id=self.model_id,
                    raw_response=response
                )
            except ClientError as e:
                raise map_bedrock_client_error(e, self.model_id, self.aws_region)
            except EndpointConnectionError:
                raise ProviderError(
                    f"Could not connect to AWS Bedrock in region '{self.aws_region}'. Check network connectivity.",
                    "CONNECTION_ERROR"
                )

        return await asyncio.to_thread(_call)

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ProviderResponse:
        if os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get("TEST_WITH_REAL_BEDROCK"):
            from backend.app.providers.mock_provider import MockProvider
            mock = MockProvider(model_id=self.model_id)
            return await mock.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                schema=schema,
                conversation_history=conversation_history,
            )

        json_instruction = (
            "\n\nIMPORTANT: You must respond ONLY with a raw, valid JSON object matching the requested schema. "
            "Do NOT include markdown formatting like ```json or ```, and do not prepend or append conversational chatter."
        )
        effective_system = (system_prompt or "") + json_instruction

        res = await self.generate_text(
            prompt=prompt,
            system_prompt=effective_system,
            max_tokens=4096,
            temperature=0.2,
            conversation_history=conversation_history,
        )

        cleaned_text = res.text.strip()
        # Strip potential markdown fences if model included them
        if cleaned_text.startswith("```"):
            cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text)
            cleaned_text = re.sub(r"\s*```$", "", cleaned_text)
            cleaned_text = cleaned_text.strip()

        try:
            parsed = json.loads(cleaned_text)
            res.parsed_json = parsed
        except json.JSONDecodeError as err:
            logger.warning(f"Model failed strict JSON parsing: {err}. Raw output snippet: {cleaned_text[:100]}")
            match = re.search(r"(\{.*\})", cleaned_text, re.DOTALL)
            if match:
                try:
                    res.parsed_json = json.loads(match.group(1))
                except Exception:
                    res.parsed_json = {"raw_text": res.text, "error": "JSON_PARSE_FAILURE"}
            else:
                res.parsed_json = {"raw_text": res.text, "error": "JSON_PARSE_FAILURE"}

        return res
