import asyncio
import json
import re
from typing import Any, Dict, List, Optional
import boto3
from botocore.exceptions import ClientError, EndpointConnectionError
from backend.app.providers.base import BaseProvider, ProviderResponse
from backend.app.providers.models_catalog import calculate_token_cost
from backend.app.core.errors import ProviderError
from backend.app.core.logging import logger

class AmazonBedrockProvider(BaseProvider):
    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_region: str = "us-east-1",
        model_id: str = "qwen.qwen3-32b-instruct-v1:0",
    ):
        super().__init__(model_id)
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region

    def _get_runtime_client(self):
        return boto3.client(
            "bedrock-runtime",
            region_name=self.aws_region,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        )

    def _get_management_client(self):
        return boto3.client(
            "bedrock",
            region_name=self.aws_region,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        )

    async def validate_credentials(self) -> bool:
        """Validate AWS IAM credentials by querying Bedrock model metadata."""
        def _check():
            try:
                client = self._get_management_client()
                client.list_foundation_models(byProvider="qwen")
                return True
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "UNKNOWN")
                if code in ("UnrecognizedClientException", "InvalidSignatureException"):
                    raise ProviderError("Invalid AWS Access Key ID or Secret Access Key.", "INVALID_CREDENTIALS")
                elif code == "AccessDeniedException":
                    # User authenticated, but might lack list_foundation_models permission; try test invocation
                    pass
                else:
                    raise ProviderError(f"AWS Bedrock verification error: {code}", "PROVIDER_ERROR")

            # Fallback check via minimal prompt invocation
            try:
                runtime = self._get_runtime_client()
                runtime.converse(
                    modelId=self.model_id,
                    messages=[{"role": "user", "content": [{"text": "ping"}]}],
                    inferenceConfig={"maxTokens": 5, "temperature": 0.0}
                )
                return True
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "UNKNOWN")
                msg = e.response.get("Error", {}).get("Message", "")
                if code in ("UnrecognizedClientException", "InvalidSignatureException"):
                    raise ProviderError("Invalid AWS Access Key ID or Secret Access Key.", "INVALID_CREDENTIALS")
                elif code == "AccessDeniedException":
                    raise ProviderError("IAM permissions issue: ensure your policy allows bedrock:InvokeModel and that Model Access is granted in the AWS Bedrock Console.", "PERMISSION_DENIED")
                elif code == "ResourceNotFoundException" or "model" in msg.lower():
                    raise ProviderError(f"Selected model '{self.model_id}' is unavailable or not granted access in region '{self.aws_region}'.", "MODEL_UNAVAILABLE")
                else:
                    raise ProviderError(f"Bedrock access error: {code}", "PROVIDER_ERROR")
            except EndpointConnectionError:
                raise ProviderError(f"Could not connect to AWS Bedrock in region '{self.aws_region}'. Check region name and network connectivity.", "CONNECTION_ERROR")

        return await asyncio.to_thread(_check)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ProviderResponse:
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

                output_text = response["output"]["message"]["content"][0]["text"]
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
                code = e.response.get("Error", {}).get("Code", "UNKNOWN")
                if code == "ThrottlingException":
                    raise ProviderError("Amazon Bedrock rate limit exceeded. Please wait a moment and retry.", "THROTTLED")
                elif code == "AccessDeniedException":
                    raise ProviderError("Access denied invoking Amazon Bedrock model. Check IAM permissions and model access in AWS console.", "PERMISSION_DENIED")
                else:
                    raise ProviderError(f"Bedrock invocation failed: {code}", "INFERENCE_ERROR")

        return await asyncio.to_thread(_call)

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ProviderResponse:
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
            # Try searching for outermost brackets
            match = re.search(r"(\{.*\})", cleaned_text, re.DOTALL)
            if match:
                try:
                    res.parsed_json = json.loads(match.group(1))
                except Exception:
                    res.parsed_json = {"raw_text": res.text, "error": "JSON_PARSE_FAILURE"}
            else:
                res.parsed_json = {"raw_text": res.text, "error": "JSON_PARSE_FAILURE"}

        return res
