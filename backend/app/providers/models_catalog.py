import json
from typing import Any, Dict, List, Optional
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
    inference_profile_id: Optional[str] = None
    supports_structured_output: bool = True
    supports_tool_calling: bool = True
    supports_streaming: bool = True
    supports_vision: bool = False

# Explicit Server-Side Model Registry for Amazon Bedrock BYOC
SUPPORTED_MODELS: Dict[str, ModelMetadata] = {
    # 1. Default General-Purpose Interview Model: Amazon Nova Lite
    "amazon.nova-lite-v1:0": ModelMetadata(
        model_id="amazon.nova-lite-v1:0",
        provider="bedrock",
        display_name="Amazon Nova Lite",
        role="Default general-purpose interview model",
        description="High-speed, cost-effective multimodal model optimal for natural interview dialogue, adaptive follow-ups, and structured question-level evaluation.",
        supported_regions=["us-east-1", "us-west-2", "ap-southeast-2", "ap-south-1", "eu-central-1"],
        input_price_per_1m=0.06,
        output_price_per_1m=0.24,
        context_window=300000,
        max_output_tokens=5000,
        recommended_for="Primary live interview questioning, dynamic conversational follow-ups, and initial feedback.",
        is_default=True,
        inference_profile_id="us.amazon.nova-lite-v1:0",
        supports_vision=True
    ),

    # 2. Stronger Reasoning & In-Depth Architecture Model: Amazon Nova Pro
    "amazon.nova-pro-v1:0": ModelMetadata(
        model_id="amazon.nova-pro-v1:0",
        provider="bedrock",
        display_name="Amazon Nova Pro",
        role="Stronger model for complex evaluation & system design",
        description="Advanced reasoning model designed for complex multi-step technical evaluations, distributed system design trade-offs, and nuanced code reviews.",
        supported_regions=["us-east-1", "us-west-2", "eu-central-1"],
        input_price_per_1m=0.80,
        output_price_per_1m=3.20,
        context_window=300000,
        max_output_tokens=5000,
        recommended_for="Final comprehensive evaluation, complex system design trade-offs, and rigorous Planly curricula generation.",
        inference_profile_id="us.amazon.nova-pro-v1:0",
        supports_vision=True
    ),

    # 3. Lightweight Fast Model: Amazon Nova Micro
    "amazon.nova-micro-v1:0": ModelMetadata(
        model_id="amazon.nova-micro-v1:0",
        provider="bedrock",
        display_name="Amazon Nova Micro",
        role="Lightweight text model for fast classification & screening",
        description="Ultra-low latency text-only model ideal for quick hint generation, response classification, and rapid topic transitions.",
        supported_regions=["us-east-1", "us-west-2", "ap-south-1", "eu-central-1"],
        input_price_per_1m=0.035,
        output_price_per_1m=0.14,
        context_window=128000,
        max_output_tokens=4096,
        recommended_for="Quick hint generation, topic categorization, and low-latency screening questions.",
        inference_profile_id="us.amazon.nova-micro-v1:0",
        supports_vision=False
    ),

    # 4. Coding Specialist: Qwen3 Coder 30B
    "qwen.qwen3-coder-30b-a3b-v1:0": ModelMetadata(
        model_id="qwen.qwen3-coder-30b-a3b-v1:0",
        provider="bedrock",
        display_name="Qwen3 Coder 30B A3B",
        role="Coding specialist",
        description="Specialized code reasoning. Use it for code explanations, debugging hints, complexity analysis, and DSA follow-up questions.",
        supported_regions=["ap-southeast-2", "us-east-1", "us-west-2", "ap-south-1"],
        input_price_per_1m=0.1545,
        output_price_per_1m=0.618,
        context_window=131072,
        max_output_tokens=8192,
        recommended_for="DSA interview code review, debugging hints, algorithmic complexity discussions."
    ),

    # 5. High-Capacity Technical Generalist: Qwen3 32B
    "qwen.qwen3-32b-instruct-v1:0": ModelMetadata(
        model_id="qwen.qwen3-32b-instruct-v1:0",
        provider="bedrock",
        display_name="Qwen3 32B",
        role="Alternative interview model",
        description="Proven open-weight instruction model on Bedrock for technical domains and system design questioning.",
        supported_regions=["ap-southeast-2", "us-east-1", "us-west-2", "ap-south-1"],
        input_price_per_1m=0.1545,
        output_price_per_1m=0.618,
        context_window=131072,
        max_output_tokens=8192,
        recommended_for="Domain-specific technical interviews and conversational follow-ups."
    )
}

DEFAULT_MODEL_ID = "amazon.nova-lite-v1:0"
DEFAULT_CODING_MODEL_ID = "amazon.nova-lite-v1:0"
DEFAULT_EVALUATION_MODEL_ID = "amazon.nova-pro-v1:0"

def get_model_metadata(model_id: str) -> Optional[ModelMetadata]:
    return SUPPORTED_MODELS.get(model_id)

def get_recommended_lineup() -> List[ModelMetadata]:
    return list(SUPPORTED_MODELS.values())

def calculate_token_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    meta = get_model_metadata(model_id)
    if not meta:
        # Fallback to Nova Lite rates if unknown
        meta = SUPPORTED_MODELS[DEFAULT_MODEL_ID]
    cost_in = (input_tokens / 1_000_000.0) * meta.input_price_per_1m
    cost_out = (output_tokens / 1_000_000.0) * meta.output_price_per_1m
    return round(cost_in + cost_out, 6)

def generate_iam_policy(model_id: str, aws_region: str, aws_account_id: str = "*") -> Dict[str, Any]:
    """
    Generates a least-privilege AWS IAM policy JSON document granting ONLY
    the minimum required inference permissions for the selected Bedrock model.
    Accounts for foundation model ARNs and inference profile ARNs.
    """
    meta = get_model_metadata(model_id)
    resources: List[str] = [
        f"arn:aws:bedrock:{aws_region}::foundation-model/{model_id}",
        f"arn:aws:bedrock:*::foundation-model/{model_id}"
    ]

    if meta and meta.inference_profile_id:
        resources.append(
            f"arn:aws:bedrock:{aws_region}:{aws_account_id}:inference-profile/{meta.inference_profile_id}"
        )
        resources.append(
            f"arn:aws:bedrock:*:{aws_account_id}:inference-profile/{meta.inference_profile_id}"
        )

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "SkillIssueBedrockModelInference",
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                "Resource": sorted(list(set(resources)))
            }
        ]
    }

    return {
        "policy_json": json.dumps(policy, indent=2),
        "model_id": model_id,
        "region": aws_region,
        "actions_explained": {
            "bedrock:InvokeModel": "Allows synchronous text and JSON generation for interview questions, follow-ups, and evaluations.",
            "bedrock:InvokeModelWithResponseStream": "Allows streaming model responses for low-latency conversational feedback."
        },
        "resources_explained": [
            f"Restricted exclusively to model '{model_id}' in region '{aws_region}' and cross-region inference profiles."
        ],
        "setup_notes": [
            "1. In the AWS Bedrock Console, ensure 'Model Access' is requested and active for the chosen model in your region.",
            "2. Attach this policy to an IAM user or role with programmatic access keys.",
            "3. Do not grant administrator access or bedrock:*."
        ]
    }
