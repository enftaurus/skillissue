# 18. Azure OpenAI BYOC Provider for Student Accessibility

Date: 2026-10-28
Status: accepted

## Context & Problem Statement

Skill Issue's primary target audience is engineering students preparing for technical interviews. In ADR-0003, Amazon Bedrock was adopted as the initial Bring-Your-Own-Cloud (BYOC) provider. However, in practice, university students face significant friction onboarding to AWS:
1. AWS requires a personal credit card for registration.
2. Foundation model access approvals (specifically cross-region inference profiles for Qwen and DeepSeek) often take several days or are rejected on new, unverified accounts.
3. AWS Budgets setup is unintuitive for students unfamiliar with cloud cost management.

In contrast, **Azure for Students** provides university students with \$100 in annual cloud credits without requiring a credit card (via GitHub Student Developer Pack or `.edu` email authentication). Azure OpenAI Service provides direct access to GPT-4o, GPT-4o-mini, and Microsoft Phi models.

We need to extend Skill Issue's provider architecture to support Azure OpenAI alongside AWS Bedrock, allowing students to select their cloud of choice during onboarding.

## Decision Drivers

- **Zero-Friction Student Access**: Enable students with Azure student credits to prepare for interviews immediately without entering a credit card.
- **Service Quality Parity**: Maintain or exceed the quality of live interviews, coding hints, and rubric evaluations using `gpt-4o-mini` and `gpt-4o`.
- **Zero Secret Leaks**: Apply identical security standards—Azure API keys must be AES-256 encrypted at rest, isolated per tenant, and never logged or exposed in client bundles.
- **Proactive Cost Protection**: Educate and warn students during onboarding to configure billing alerts in both Azure Cost Management and AWS Budgets.

## Considered Options

1. **Keep AWS Bedrock as the sole BYOC provider**: Rejected due to high drop-off among university students who lack credit cards or model access.
2. **Add a multi-provider LiteLLM gateway**: Rejected (as in ADR-0003) to avoid third-party proxy dependencies and security attack surfaces.
3. **Native `AzureOpenAIProvider` within Application-Owned Model Factory**: Selected. Directly inherits from `BaseProvider` and integrates with `ModelClientFactory` and LangGraph using `openai` and `langchain-openai`.

## Decision Outcome

Accepted. Implement `AzureOpenAIProvider` as a first-class BYOC provider alongside `AmazonBedrockProvider`:

### 1. Model Role Allocation for Azure
- **Interviewer & Conversational Agent**: `azure.gpt-4o-mini` — ~180ms TTFT, strict constraint adherence (under 3 sentences, zero praise), minimal cost (\$0.15 / 1M in, \$0.60 / 1M out).
- **Evaluator & Rubric Grader**: `azure.gpt-4o` — High-depth reasoning, native JSON schema adherence, verifiable evidence extraction (\$2.50 / 1M in, \$10.00 / 1M out).
- **Coding Arena Coach & Hints**: `azure.gpt-4o-mini` / `azure.phi-3.5-mini` — Socratic guidance without revealing LeetCode answers.
- **Planly Adaptive Scheduler**: `azure.gpt-4o-mini` — Fast curriculum generation.

### 2. Dual-Cloud Onboarding UX
The onboarding wizard allows students to choose:
1. **Microsoft Azure (Recommended for Students)**:
   - Guided steps for Azure OpenAI Resource creation, model deployments, and API key retrieval.
   - Prominent billing alert warning to set Azure Cost Management budget alerts.
2. **Amazon Web Services (Bedrock)**:
   - Guided steps for Bedrock Model Access, least-privilege IAM policy generation, and Access Key retrieval.
   - Prominent billing alert warning to set AWS Budgets.

### 3. Credential Security
Azure API keys and endpoints are encrypted at rest with AES-256/Fernet using `SKILLISSUE_SECRET_KEY`. Keys are decrypted only into transient process memory when executing requests.

## Consequences

### Positive
- Students with Azure for Students can onboard and practice immediately with zero monetary investment.
- GPT-4o-mini provides exceptional negative prompt adherence (Gilfoyle tone, zero flattery) and native JSON output.
- Full parity with existing bounded client cache and per-user isolation.

### Negative / Trade-offs
- Azure requires deploying models within a resource, introducing deployment name mapping.
- Azure student accounts have strict TPM (Tokens Per Minute) quotas, requiring backoff handling.
