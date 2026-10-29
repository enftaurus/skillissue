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
    # 1. Default General-Purpose Interview Model: Qwen3 32B
    "qwen.qwen3-32b-v1:0": ModelMetadata(
        model_id="qwen.qwen3-32b-v1:0",
        provider="bedrock",
        display_name="Qwen3 32B",
        role="Default general-purpose interview model",
        description="High-performance open-weight model by Qwen. Direct, technically rigorous questioning, realistic conversational follow-ups, and zero corporate fluff.",
        supported_regions=["us-east-1", "us-west-2", "ap-southeast-2", "ap-south-1"],
        input_price_per_1m=0.1545,
        output_price_per_1m=0.618,
        context_window=131072,
        max_output_tokens=8192,
        recommended_for="Primary live technical interviews, distributed systems, and dynamic conversational follow-ups.",
        is_default=True,
    ),

    # 2. Coding Specialist: Qwen3 Coder 30B
    "qwen.qwen3-coder-30b-a3b-v1:0": ModelMetadata(
        model_id="qwen.qwen3-coder-30b-a3b-v1:0",
        provider="bedrock",
        display_name="Qwen3 Coder 30B A3B",
        role="Coding specialist",
        description="Specialized code reasoning model by Qwen. Socratic hint generation, DSA code review, complexity analysis, and debugging hints.",
        supported_regions=["us-east-1", "us-west-2", "ap-southeast-2", "ap-south-1"],
        input_price_per_1m=0.1545,
        output_price_per_1m=0.618,
        context_window=131072,
        max_output_tokens=8192,
        recommended_for="DSA Arena Socratic coaching, code review, debugging hints, and complexity analysis."
    ),

    # 3. Technical Interviewer & Architecture Specialist: DeepSeek V3.2
    "deepseek.v3.2": ModelMetadata(
        model_id="deepseek.v3.2",
        provider="bedrock",
        display_name="DeepSeek V3.2",
        role="Advanced technical interview & systems specialist",
        description="Leading open MoE model by DeepSeek. Unforgiving technical depth, concurrency probing, and distributed architecture trade-offs at ultra-low cost.",
        supported_regions=["us-east-1", "us-west-2"],
        input_price_per_1m=0.14,
        output_price_per_1m=0.28,
        context_window=131072,
        max_output_tokens=8192,
        recommended_for="Senior/Staff systems engineering interviews, concurrency, and architecture design."
    ),

    # 4. In-Depth Evaluation & Reasoning: DeepSeek-R1
    "us.deepseek.r1-v1:0": ModelMetadata(
        model_id="us.deepseek.r1-v1:0",
        provider="bedrock",
        display_name="DeepSeek-R1 (Reasoning)",
        role="Comprehensive evaluation & weakness analysis",
        description="Frontier reasoning model with chain-of-thought verification. Rigorous rubric scoring, complexity audits, and weakness taxonomy synthesis.",
        supported_regions=["us-east-1", "us-west-2", "us-east-2"],
        input_price_per_1m=0.55,
        output_price_per_1m=2.19,
        context_window=131072,
        max_output_tokens=8192,
        inference_profile_id="us.deepseek.r1-v1:0",
        recommended_for="Post-interview rubric evaluation, comprehensive feedback reports, and Planly weakness extraction."
    ),

    # 5. High-Capacity Generalist: Qwen3 Next 80B
    "qwen.qwen3-next-80b-a3b": ModelMetadata(
        model_id="qwen.qwen3-next-80b-a3b",
        provider="bedrock",
        display_name="Qwen3 Next 80B A3B",
        role="High-capacity generalist",
        description="High-parameter open model by Qwen for cross-domain engineering discussions and deep conceptual trade-offs.",
        supported_regions=["us-east-1", "us-west-2"],
        input_price_per_1m=0.30,
        output_price_per_1m=1.20,
        context_window=131072,
        max_output_tokens=8192,
        recommended_for="Broad technical rounds and cross-disciplinary architecture reviews."
    ),

    # 6. Ultra-Budget Fallback: Amazon Nova Lite
    "amazon.nova-lite-v1:0": ModelMetadata(
        model_id="amazon.nova-lite-v1:0",
        provider="bedrock",
        display_name="Amazon Nova Lite",
        role="Budget general-purpose model",
        description="Ultra-low cost text model for lightweight testing.",
        supported_regions=["us-east-1", "us-west-2", "ap-southeast-2", "ap-south-1", "eu-central-1"],
        input_price_per_1m=0.06,
        output_price_per_1m=0.24,
        context_window=300000,
        max_output_tokens=5000,
        recommended_for="Low-cost screening and budget fallback.",
        is_default=False,
        inference_profile_id="us.amazon.nova-lite-v1:0",
        supports_vision=True
    ),

    # 7. Secondary Evaluation Option: Amazon Nova Pro
    "amazon.nova-pro-v1:0": ModelMetadata(
        model_id="amazon.nova-pro-v1:0",
        provider="bedrock",
        display_name="Amazon Nova Pro",
        role="Secondary evaluation model",
        description="Multimodal reasoning model for evaluations.",
        supported_regions=["us-east-1", "us-west-2", "eu-central-1"],
        input_price_per_1m=0.80,
        output_price_per_1m=3.20,
        context_window=300000,
        max_output_tokens=5000,
        recommended_for="Secondary evaluation option.",
        inference_profile_id="us.amazon.nova-pro-v1:0",
        supports_vision=True
    ),

    # 8. Lightweight Fast Model: Amazon Nova Micro
    "amazon.nova-micro-v1:0": ModelMetadata(
        model_id="amazon.nova-micro-v1:0",
        provider="bedrock",
        display_name="Amazon Nova Micro",
        role="Lightweight text model",
        description="Ultra-low latency text-only model.",
        supported_regions=["us-east-1", "us-west-2", "ap-south-1", "eu-central-1"],
        input_price_per_1m=0.035,
        output_price_per_1m=0.14,
        context_window=128000,
        max_output_tokens=4096,
        recommended_for="Quick hint generation and screening.",
        inference_profile_id="us.amazon.nova-micro-v1:0",
        supports_vision=False
    ),

    # 9. Azure OpenAI: GPT-4o Mini (Default for Azure Students)
    "azure.gpt-4o-mini": ModelMetadata(
        model_id="azure.gpt-4o-mini",
        provider="azure",
        display_name="GPT-4o Mini (Azure OpenAI)",
        role="Fast conversational interviewer & coding coach",
        description="High-speed, cost-efficient multimodal model on Azure. Outstanding constraint adherence, rapid response, and ideal for students.",
        supported_regions=["eastus", "eastus2", "westus", "westus3", "swedencentral", "japaneast"],
        input_price_per_1m=0.15,
        output_price_per_1m=0.60,
        context_window=128000,
        max_output_tokens=16384,
        recommended_for="Primary live technical interviews, DSA hint coaching, and rapid back-and-forth turns.",
        supports_vision=True,
    ),

    # 10. Azure OpenAI: GPT-4o (Deep Evaluator for Azure Students)
    "azure.gpt-4o": ModelMetadata(
        model_id="azure.gpt-4o",
        provider="azure",
        display_name="GPT-4o (Azure OpenAI)",
        role="Flagship evaluator & rubric grader",
        description="Flagship multimodal model by OpenAI on Azure. Deep reasoning, precise rubric grading, evidence citation, and zero hallucinated scores.",
        supported_regions=["eastus", "eastus2", "westus", "westus3", "swedencentral", "japaneast"],
        input_price_per_1m=2.50,
        output_price_per_1m=10.00,
        context_window=128000,
        max_output_tokens=4096,
        recommended_for="Comprehensive interview evaluation, weakness detection, and senior-level rubric calibration.",
        supports_vision=True,
    ),

    # 11. Azure AI: Microsoft Phi-3.5 Mini (Lightweight Helper)
    "azure.phi-3.5-mini": ModelMetadata(
        model_id="azure.phi-3.5-mini",
        provider="azure",
        display_name="Microsoft Phi-3.5 Mini (Azure AI)",
        role="Lightweight coding helper",
        description="Small 3.8B language model by Microsoft on Azure AI. Ultra-low latency and token consumption for student subscriptions.",
        supported_regions=["eastus", "westus2", "swedencentral"],
        input_price_per_1m=0.05,
        output_price_per_1m=0.15,
        context_window=128000,
        max_output_tokens=4096,
        recommended_for="Lightweight DSA coaching and token-restricted student subscriptions.",
        supports_vision=False,
    ),

    # 12. Azure OpenAI: GPT-4.1 (Next-Gen Flagship Coding & Reasoning)
    "azure.gpt-4.1": ModelMetadata(
        model_id="azure.gpt-4.1",
        provider="azure",
        display_name="GPT-4.1 (Azure OpenAI)",
        role="Next-gen coding & reasoning flagship",
        description="Next-generation flagship model on Azure OpenAI with advanced multi-step coding, 1M token context, and state-of-the-art instruction adherence.",
        supported_regions=["eastus", "eastus2", "westus", "westus3", "swedencentral"],
        input_price_per_1m=2.00,
        output_price_per_1m=8.00,
        context_window=1000000,
        max_output_tokens=16384,
        recommended_for="Deep architectural problem solving, complex repository tasks, and rubric evaluations.",
        supports_vision=True,
    ),

    # 13. Azure OpenAI: GPT-4.1 Mini (High-Throughput Fast Tier)
    "azure.gpt-4.1-mini": ModelMetadata(
        model_id="azure.gpt-4.1-mini",
        provider="azure",
        display_name="GPT-4.1 Mini (Azure OpenAI)",
        role="Fast conversational interviewer & coding coach",
        description="Fast, low-latency GPT-4.1 tier on Azure OpenAI. Excellent for dynamic technical interview turns and real-time DSA hints.",
        supported_regions=["eastus", "eastus2", "westus", "westus3", "swedencentral"],
        input_price_per_1m=0.20,
        output_price_per_1m=0.80,
        context_window=1000000,
        max_output_tokens=16384,
        recommended_for="Live dynamic technical interview turns and high-speed coding hints.",
        supports_vision=True,
    ),
}

DEFAULT_MODEL_ID = "qwen.qwen3-32b-v1:0"
DEFAULT_CODING_MODEL_ID = "qwen.qwen3-coder-30b-a3b-v1:0"
DEFAULT_EVALUATION_MODEL_ID = "us.deepseek.r1-v1:0"

DEFAULT_AZURE_MODEL_ID = "azure.gpt-4.1-mini"
DEFAULT_AZURE_CODING_MODEL_ID = "azure.gpt-4.1-mini"
DEFAULT_AZURE_EVALUATION_MODEL_ID = "azure.gpt-4.1"

def get_model_metadata(model_id: str) -> Optional[ModelMetadata]:
    return SUPPORTED_MODELS.get(model_id)

def get_recommended_lineup() -> List[ModelMetadata]:
    return list(SUPPORTED_MODELS.values())

def calculate_token_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    meta = get_model_metadata(model_id)
    if not meta:
        # Fallback to default Qwen rates if unknown
        meta = SUPPORTED_MODELS[DEFAULT_MODEL_ID]
    cost_in = (input_tokens / 1_000_000.0) * meta.input_price_per_1m
    cost_out = (output_tokens / 1_000_000.0) * meta.output_price_per_1m
    return round(cost_in + cost_out, 6)

def generate_iam_policy(model_id: str, aws_region: str, aws_account_id: str = "*") -> Dict[str, Any]:
    """
    Generates a least-privilege AWS IAM policy JSON document granting ONLY
    the minimum required inference permissions for the selected Bedrock model(s).
    Accounts for foundation model ARNs and inference profile ARNs across all selected models and regions.
    """
    if isinstance(model_id, str):
        model_ids = [m.strip() for m in model_id.split(",") if m.strip()]
    elif isinstance(model_id, (list, tuple, set)):
        model_ids = [str(m).strip() for m in model_id if str(m).strip()]
    else:
        model_ids = [str(model_id)]

    if isinstance(aws_region, str):
        regions = [r.strip() for r in aws_region.split(",") if r.strip()]
    elif isinstance(aws_region, (list, tuple, set)):
        regions = [str(r).strip() for r in aws_region if str(r).strip()]
    else:
        regions = [str(aws_region)]

    if not model_ids:
        model_ids = [DEFAULT_MODEL_ID]
    if not regions:
        regions = ["us-east-1"]

    resources = set()
    for mid in model_ids:
        meta = get_model_metadata(mid)
        for reg in regions:
            resources.add(f"arn:aws:bedrock:{reg}::foundation-model/{mid}")
            resources.add(f"arn:aws:bedrock:*::foundation-model/{mid}")

            # Handle inference profile models (e.g. us.deepseek.r1-v1:0)
            if mid.startswith(("us.", "eu.")):
                base_model = mid.split(".", 1)[1]
                resources.add(f"arn:aws:bedrock:{reg}::foundation-model/{base_model}")
                resources.add(f"arn:aws:bedrock:*::foundation-model/{base_model}")
                resources.add(f"arn:aws:bedrock:{reg}:{aws_account_id}:inference-profile/{mid}")
                resources.add(f"arn:aws:bedrock:*:{aws_account_id}:inference-profile/{mid}")

            if meta and meta.inference_profile_id:
                prof = meta.inference_profile_id
                resources.add(f"arn:aws:bedrock:{reg}:{aws_account_id}:inference-profile/{prof}")
                resources.add(f"arn:aws:bedrock:*:{aws_account_id}:inference-profile/{prof}")
                if prof.startswith(("us.", "eu.")):
                    base_model = prof.split(".", 1)[1]
                    resources.add(f"arn:aws:bedrock:{reg}::foundation-model/{base_model}")
                    resources.add(f"arn:aws:bedrock:*::foundation-model/{base_model}")

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
                "Resource": sorted(list(resources))
            }
        ]
    }

    policy_rendered = json.dumps(policy, indent=2)
    return {
        "policy_json": policy_rendered,
        "policy_document": policy_rendered,
        "model_id": model_id,
        "region": aws_region,
        "actions_explained": {
            "bedrock:InvokeModel": "Allows synchronous text and JSON generation for interview questions, follow-ups, and evaluations.",
            "bedrock:InvokeModelWithResponseStream": "Allows streaming model responses for low-latency conversational feedback."
        },
        "resources_explained": [
            f"Restricted exclusively to model(s) '{', '.join(model_ids)}' in region(s) '{', '.join(regions)}' and associated cross-region inference profiles."
        ],
        "setup_notes": [
            "1. In the AWS Bedrock Console, ensure 'Model Access' is requested and active for the chosen model(s) in your region(s).",
            "2. Attach this policy to an IAM user or role with programmatic access keys.",
            "3. Do not grant administrator access or bedrock:*."
        ]
    }
