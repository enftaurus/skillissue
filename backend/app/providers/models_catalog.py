from typing import Dict, List, Optional
from pydantic import BaseModel

class ModelMetadata(BaseModel):
    model_id: str
    provider: str
    display_name: str
    role: str
    description: str
    supported_regions: List[str]
    input_price_per_1m: float  # USD per 1,000,000 input tokens
    output_price_per_1m: float  # USD per 1,000,000 output tokens
    context_window: int
    max_output_tokens: int
    recommended_for: str
    is_default: bool = False
    supports_structured_output: bool = True
    supports_tool_calling: bool = True
    supports_streaming: bool = True
    supports_vision: bool = False

# Recommended Model Lineup for Skill Issue (per explicit product owner specification)
SUPPORTED_MODELS: Dict[str, ModelMetadata] = {
    # 1. Primary Interview Model: Qwen3 32B
    "qwen.qwen3-32b-instruct-v1:0": ModelMetadata(
        model_id="qwen.qwen3-32b-instruct-v1:0",
        provider="bedrock",
        display_name="Qwen3 32B",
        role="Primary interview model",
        description="Start here. Exceptional cost-efficiency for natural interview questions, adaptive follow-ups, system-design questioning, and first-pass evaluation.",
        supported_regions=["ap-southeast-2", "us-east-1", "us-west-2", "ap-south-1"],
        input_price_per_1m=0.1545,
        output_price_per_1m=0.618,
        context_window=131072,
        max_output_tokens=8192,
        recommended_for="Natural interview questions, adaptive follow-ups, system-design questioning, and first-pass evaluation.",
        is_default=True
    ),

    # 2. Coding Specialist: Qwen3 Coder 30B A3B
    "qwen.qwen3-coder-30b-a3b-v1:0": ModelMetadata(
        model_id="qwen.qwen3-coder-30b-a3b-v1:0",
        provider="bedrock",
        display_name="Qwen3 Coder 30B A3B",
        role="Coding specialist",
        description="Specialized code reasoning. Use it for code explanations, debugging hints, complexity analysis, and follow-up questions about implementation choices.",
        supported_regions=["ap-southeast-2", "us-east-1", "us-west-2", "ap-south-1"],
        input_price_per_1m=0.1545,
        output_price_per_1m=0.618,
        context_window=131072,
        max_output_tokens=8192,
        recommended_for="Code explanations, debugging hints, complexity analysis, and follow-ups on implementation choices."
    ),

    # 3. Stronger-Model Comparison: Qwen3 Next 80B A3B
    "qwen.qwen3-next-80b-a3b-v1:0": ModelMetadata(
        model_id="qwen.qwen3-next-80b-a3b-v1:0",
        provider="bedrock",
        display_name="Qwen3 Next 80B A3B",
        role="Stronger-model comparison",
        description="Benchmark it for nuanced evaluation, difficult trade-offs, and complex system-design answers. Keep it only if it demonstrably improves quality.",
        supported_regions=["ap-south-1", "us-east-1", "us-west-2"],
        input_price_per_1m=0.18,
        output_price_per_1m=1.41,
        context_window=131072,
        max_output_tokens=8192,
        recommended_for="Nuanced evaluation, difficult trade-offs, and complex system-design depth."
    ),

    # 4. Premium Reasoning and Vision Experiment: Kimi K3
    "moonshot.kimi-k3-v1:0": ModelMetadata(
        model_id="moonshot.kimi-k3-v1:0",
        provider="bedrock",
        display_name="Kimi K3",
        role="Premium reasoning & vision experiment",
        description="Test it for complex architecture reviews or interpreting screenshots when structured diagrams are insufficient. Long context and vision capabilities; higher pricing makes it unsuitable as default.",
        supported_regions=["ap-south-1", "us-east-1"],
        input_price_per_1m=3.30,
        output_price_per_1m=16.50,
        context_window=200000,
        max_output_tokens=8192,
        recommended_for="Complex architecture reviews, diagrams, and vision/screenshot analysis.",
        supports_vision=True
    ),

    # 5. Local Mock Engine for zero-cost offline development & automated tests
    "mock-qwen3-32b": ModelMetadata(
        model_id="mock-qwen3-32b",
        provider="mock",
        display_name="Local Mock Engine (Offline Dev)",
        role="Local development & automated testing",
        description="Deterministic, zero-cost local provider generating realistic questions, follow-ups, and rubric evaluations without AWS keys.",
        supported_regions=["local"],
        input_price_per_1m=0.00,
        output_price_per_1m=0.00,
        context_window=131072,
        max_output_tokens=8192,
        recommended_for="Local development and automated testing without AWS credentials."
    )
}

DEFAULT_MODEL_ID = "qwen.qwen3-32b-instruct-v1:0"
DEFAULT_CODING_MODEL_ID = "qwen.qwen3-coder-30b-a3b-v1:0"
DEFAULT_EVALUATION_MODEL_ID = "qwen.qwen3-32b-instruct-v1:0"
MOCK_MODEL_ID = "mock-qwen3-32b"

def get_model_metadata(model_id: str) -> Optional[ModelMetadata]:
    return SUPPORTED_MODELS.get(model_id)

def get_recommended_lineup() -> List[ModelMetadata]:
    return list(SUPPORTED_MODELS.values())

def calculate_token_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    meta = get_model_metadata(model_id)
    if not meta:
        return 0.0
    cost_in = (input_tokens / 1_000_000.0) * meta.input_price_per_1m
    cost_out = (output_tokens / 1_000_000.0) * meta.output_price_per_1m
    return round(cost_in + cost_out, 6)
