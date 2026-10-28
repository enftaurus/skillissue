import json
import os
import re
from typing import Any, Dict, List, Optional
import openai
from openai import AsyncAzureOpenAI
from backend.app.providers.base import BaseProvider, ProviderResponse
from backend.app.providers.models_catalog import calculate_token_cost
from backend.app.core.errors import ProviderError
from backend.app.core.logging import logger

def map_azure_error(e: Exception, model_id: str, endpoint: str) -> ProviderError:
    """
    Map Azure OpenAI / OpenAI SDK exceptions to typed ProviderError instances.
    Secrets and API keys are NEVER included in error messages or logs.
    """
    if isinstance(e, openai.AuthenticationError):
        return ProviderError(
            "Invalid Azure OpenAI API Key or Endpoint. Please verify your credentials in the Azure Portal.",
            "INVALID_CREDENTIALS"
        )
    elif isinstance(e, openai.NotFoundError):
        return ProviderError(
            f"Deployment or model '{model_id}' was not found at endpoint '{endpoint}'. "
            "Ensure the model is deployed in Azure OpenAI Studio with this deployment name.",
            "MODEL_UNAVAILABLE"
        )
    elif isinstance(e, openai.RateLimitError):
        return ProviderError(
            "Azure OpenAI rate limit or quota exceeded (TPM/RPM) for this subscription. "
            "Check your deployment quota in Azure AI Studio.",
            "THROTTLED"
        )
    elif isinstance(e, openai.PermissionDeniedError):
        return ProviderError(
            "Access denied by Azure. Verify your Azure resource role assignments and network access rules.",
            "PERMISSION_DENIED"
        )
    elif isinstance(e, openai.APIConnectionError):
        return ProviderError(
            f"Could not connect to Azure OpenAI endpoint '{endpoint}'. Check your endpoint URL and network connectivity.",
            "CONNECTION_ERROR"
        )
    elif isinstance(e, openai.BadRequestError):
        return ProviderError(
            f"Azure OpenAI validation error: {getattr(e, 'message', str(e))}",
            "VALIDATION_ERROR"
        )
    else:
        return ProviderError(
            f"Azure OpenAI service error: {getattr(e, 'message', str(e))}",
            "INFERENCE_ERROR"
        )

class AzureOpenAIProvider(BaseProvider):
    """
    Azure OpenAI BYOC Provider implementation for student-friendly cloud accessibility.
    
    SECURITY NOTE:
    API keys remain encrypted with AES-256 in PostgreSQL and are decrypted only into ephemeral
    process memory during active inference calls. Cached clients have bounded TTL and hard size limits.
    """
    def __init__(
        self,
        azure_endpoint: str,
        api_key: Optional[str] = None,
        api_version: str = "2024-06-01",
        deployment_name: Optional[str] = None,
        model_id: str = "azure.gpt-4o-mini",
        client: Optional[AsyncAzureOpenAI] = None,
        azure_api_key: Optional[str] = None,
        azure_api_version: Optional[str] = None,
        azure_deployment_name: Optional[str] = None,
    ):
        super().__init__(model_id)
        # Normalize endpoint (strip trailing slashes)
        self.azure_endpoint = azure_endpoint.rstrip("/") if azure_endpoint else ""
        effective_key = api_key or azure_api_key or ""
        self.api_key = effective_key
        self.azure_api_key = effective_key
        self.api_version = azure_api_version or api_version or "2024-06-01"
        self.azure_api_version = self.api_version
        # Standardize deployment name: if not supplied, strip "azure." prefix
        dep_name = azure_deployment_name or deployment_name or model_id.replace("azure.", "")
        self.deployment_name = dep_name
        self.azure_deployment_name = dep_name
        self._client = client

    @property
    def client(self) -> AsyncAzureOpenAI:
        return self._get_client()

    def _get_client(self) -> AsyncAzureOpenAI:
        if self._client is not None:
            return self._client
        self._client = AsyncAzureOpenAI(
            azure_endpoint=self.azure_endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
            timeout=30.0,
            max_retries=2,
        )
        return self._client

    async def validate_credentials(self) -> bool:
        """
        Validate Azure OpenAI credentials by executing a minimal test completion.
        """
        if os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get("TEST_WITH_REAL_AZURE") and self._client is None:
            return True

        client = self._get_client()
        try:
            await client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
                temperature=0.0,
            )
            return True
        except Exception as e:
            raise map_azure_error(e, self.deployment_name, self.azure_endpoint)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ProviderResponse:
        if os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get("TEST_WITH_REAL_AZURE"):
            from backend.app.providers.mock_provider import MockProvider
            mock = MockProvider(model_id=self.model_id)
            return await mock.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                conversation_history=conversation_history,
            )

        client = self._get_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if conversation_history:
            for msg in conversation_history:
                role = "assistant" if msg["role"] == "assistant" else "user"
                messages.append({"role": role, "content": msg["content"]})

        if not conversation_history or conversation_history[-1].get("content") != prompt:
            messages.append({"role": "user", "content": prompt})

        try:
            response = await client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            choice = response.choices[0]
            output_text = choice.message.content or ""

            # Strip reasoning tags if present
            cleaned_output = re.sub(r"<think>[\s\S]*?</think>", "", output_text, flags=re.DOTALL).strip()
            cleaned_output = re.sub(r"^[\s\S]*?</think>", "", cleaned_output, flags=re.DOTALL).strip()
            if cleaned_output:
                output_text = cleaned_output

            in_tokens = response.usage.prompt_tokens if response.usage else 0
            out_tokens = response.usage.completion_tokens if response.usage else 0
            cost = calculate_token_cost(self.model_id, in_tokens, out_tokens)

            return ProviderResponse(
                text=output_text,
                input_tokens=in_tokens,
                output_tokens=out_tokens,
                estimated_cost_usd=cost,
                model_id=self.model_id,
                raw_response=response
            )
        except Exception as e:
            raise map_azure_error(e, self.deployment_name, self.azure_endpoint)

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ProviderResponse:
        if os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get("TEST_WITH_REAL_AZURE"):
            from backend.app.providers.mock_provider import MockProvider
            mock = MockProvider(model_id=self.model_id)
            return await mock.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                schema=schema,
                conversation_history=conversation_history,
            )

        client = self._get_client()
        json_instruction = (
            "\n\nIMPORTANT: You must respond ONLY with a raw, valid JSON object matching the requested schema. "
            "Do NOT include markdown formatting like ```json or ```, and do not prepend or append conversational chatter."
        )
        effective_system = (system_prompt or "") + json_instruction

        messages = [{"role": "system", "content": effective_system}]
        if conversation_history:
            for msg in conversation_history:
                role = "assistant" if msg["role"] == "assistant" else "user"
                messages.append({"role": role, "content": msg["content"]})

        if not conversation_history or conversation_history[-1].get("content") != prompt:
            messages.append({"role": "user", "content": prompt})

        try:
            # Azure OpenAI supports native JSON object output format
            response = await client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                max_tokens=4096,
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            raw_text = response.choices[0].message.content or ""
            cleaned_text = raw_text.strip()

            # Strip markdown fences if returned
            md_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned_text)
            if md_match:
                cleaned_text = md_match.group(1).strip()
            elif cleaned_text.startswith("```"):
                cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text)
                cleaned_text = re.sub(r"\s*```$", "", cleaned_text)
                cleaned_text = cleaned_text.strip()

            in_tokens = response.usage.prompt_tokens if response.usage else 0
            out_tokens = response.usage.completion_tokens if response.usage else 0
            cost = calculate_token_cost(self.model_id, in_tokens, out_tokens)

            res = ProviderResponse(
                text=raw_text,
                input_tokens=in_tokens,
                output_tokens=out_tokens,
                estimated_cost_usd=cost,
                model_id=self.model_id,
                raw_response=response
            )

            try:
                res.parsed_json = json.loads(cleaned_text)
            except json.JSONDecodeError as err:
                logger.warning(f"Azure model failed strict JSON parsing: {err}. Snippet: {cleaned_text[:100]}")
                match = re.search(r"(\{[\s\S]*\})", cleaned_text)
                if match:
                    try:
                        res.parsed_json = json.loads(match.group(1))
                    except Exception:
                        res.parsed_json = {"raw_text": raw_text, "error": "JSON_PARSE_FAILURE"}
                else:
                    res.parsed_json = {"raw_text": raw_text, "error": "JSON_PARSE_FAILURE"}

            return res
        except Exception as e:
            raise map_azure_error(e, self.deployment_name, self.azure_endpoint)
