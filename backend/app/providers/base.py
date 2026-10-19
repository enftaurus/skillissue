from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class ProviderResponse:
    text: str
    parsed_json: Optional[Dict[str, Any]] = None
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    model_id: str = ""
    raw_response: Optional[Any] = None

class BaseProvider(ABC):
    def __init__(self, model_id: str):
        self.model_id = model_id

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ProviderResponse:
        """Generate conversational text response."""
        pass

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> ProviderResponse:
        """Generate structured JSON response conforming to expected schema."""
        pass

    @abstractmethod
    async def validate_credentials(self) -> bool:
        """Validate provider credentials and verify model access."""
        pass
