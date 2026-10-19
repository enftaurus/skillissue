# ADR 0001: Modular Monolith Architecture

- **Date:** 2026-10-20
- **Status:** Accepted
- **Context:** Skill Issue requires high velocity, strong cohesion between domain models (interviews, questions, evaluations, learner plans), shared transaction boundaries, and simple local operations.
- **Decision:** Build Skill Issue as a modular monolith in FastAPI. Untrusted code execution is separated via a dedicated sandbox boundary.
- **Alternatives Considered:**
  - *Microservices*: Rejected due to operational complexity, distributed transaction overhead, and premature optimization.
  - *Serverless Functions*: Rejected due to cold starts during interactive audio/text interviews and execution timeouts.
- **Rationale:** A modular monolith maintains clean domain boundaries (`auth`, `providers`, `interviews`, `evaluations`, `plans`, `coding`) while allowing shared database sessions, zero network hop latency between services, and single-process debugging.
- **Consequences:** Code within the monolith must strictly respect module boundaries and avoid direct cross-boundary database mutations.
- **Related Requirements:** PRD Section 8.2; Master Prompt Section 6.
