# ADR 0002: Model Provider Abstraction & Factory

- **Date:** 2026-10-20
- **Status:** Accepted
- **Context:** The application needs to support Amazon Bedrock as its primary BYOC inference backend, while remaining extensible to future providers and operating fully offline during local development.
- **Decision:** Implement an application-owned `ModelFactory` and `BaseProvider` interface. Explicitly exclude LiteLLM and LangGraph from the initial architecture. Include a high-fidelity `MockProvider` for testing and local development.
- **Alternatives Considered:**
  - *LiteLLM*: Rejected to avoid extra dependency overhead, hidden proxy behaviors, and potential security boundary complications with BYOC credentials.
  - *Direct Boto3 across routes*: Rejected because it would tightly couple interview logic to AWS Bedrock and prevent mock testing.
- **Rationale:** An application-owned provider abstraction gives Skill Issue total control over error sanitization, prompt formatting, token usage logging, pricing calculations, and offline testing without depending on external proxy servers.
- **Consequences:** We maintain provider adapters ourselves, which requires explicit model catalog mapping and exception handling.
- **Related Requirements:** PRD Section 8.3; Master Prompt Section 7.
