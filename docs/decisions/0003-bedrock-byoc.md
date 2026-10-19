# ADR 0003: BYOC with Amazon Bedrock

- **Date:** 2026-10-20
- **Status:** Accepted
- **Context:** To ensure financial sustainability, zero platform markup, and direct student control over AI spending, Skill Issue adopts a Bring-Your-Own-Cloud (BYOC) model.
- **Decision:** Support Amazon Bedrock as the first inference provider. Model requests authenticate using user-configured IAM access keys. Recommend cost-effective models (e.g., Claude 3.5 Haiku, Amazon Nova Lite/Pro) with a $20 student planning budget.
- **Alternatives Considered:**
  - *Platform-funded OpenAI proxy*: Rejected because fixed hosting and inference costs would make the platform unsustainable without subscription billing.
  - *Local model installation (Ollama)*: Rejected per PRD non-goals due to student hardware disparities.
- **Rationale:** Bedrock provides enterprise-grade uptime, reliable JSON mode outputs, predictable per-token pricing, and straightforward IAM least-privilege policies.
- **Consequences:** Onboarding requires users to configure IAM credentials and model access. A clear, student-facing guide is mandatory to eliminate friction.
- **Related Requirements:** PRD FR-02; Master Prompt Section 7 & 8.
