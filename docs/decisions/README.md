# Architecture Decision Records (ADRs)

This directory contains records of all architectural, infrastructural, and security decisions made for Skill Issue.

## Decision Log Index

| ID | Title | Date | Status | Summary |
|---|---|---|---|---|
| [0001](0001-modular-monolith.md) | Modular Monolith Architecture | 2026-10-20 | Accepted | Build as a modular monolith in FastAPI rather than distributed microservices. |
| [0002](0002-provider-abstraction.md) | Model Provider Abstraction & Factory | 2026-10-20 | Accepted | Application-owned provider factory supporting Amazon Bedrock and offline Mock provider without LiteLLM. |
| [0003](0003-bedrock-byoc.md) | BYOC with Amazon Bedrock | 2026-10-20 | Accepted | Initial LLM integration via user-supplied AWS Bedrock credentials with $20 planning budget. |
| [0004](0004-postgresql-docker.md) | Containerized PostgreSQL with Docker Volume | 2026-10-20 | Accepted | Local PostgreSQL 16 on port 5433 with named volume persistence and Alembic migrations. |
| [0005](0005-credential-encryption.md) | At-Rest Credential Encryption | 2026-10-20 | Accepted | User AWS secrets encrypted using AES-256-GCM (Fernet) with strict log masking. |
| [0006](0006-interview-engine-and-rubrics.md) | Unified Interview Engine & Post-Evaluation | 2026-10-20 | Accepted | Single engine serving domain and JD interviews, separate post-interview evaluation pass. |
| [0007](0007-coding-sandbox-architecture.md) | Isolated Execution Sandbox | 2026-10-20 | Superseded by 0010 | Multi-language sandbox with ephemeral environments and resource limits. |
| [0008](0008-planly-adaptive-engine.md) | Planly Adaptive Learning Engine | 2026-10-20 | Accepted | Dynamic multi-day improvement plans adapting to missed tasks and reassessment scores. |
| [0009](0009-recommended-model-lineup.md) | Recommended Model Lineup & Task-Based Routing | 2026-10-20 | Accepted | Qwen3 32B primary, Qwen3 Coder 30B, Qwen3 Next 80B comparison, and Kimi K3 vision/reasoning. |
| [0010](0010-docker-code-execution-service.md) | Isolated Docker Code Execution Service & Threat Model | 2026-10-20 | Accepted | Real ephemeral Docker container executor service with no network, external judging, cgroups, and fail-closed safety. |

---

## ADR Process

1. Create a new markdown file named `NNNN-short-title.md`.
2. Follow standard ADR sections: Title, Date, Status, Context, Decision, Alternatives Considered, Rationale, Consequences & Trade-offs, Related Requirements.
3. Update this index.
4. When a past decision is modified, mark the previous record as `Superseded by NNNN` rather than rewriting historical records.
