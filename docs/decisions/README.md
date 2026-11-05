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
| [0010](0010-docker-code-execution-service.md) | Isolated Docker Code Execution Service & Threat Model | 2026-10-20 | Superseded by 0016 | Real ephemeral Docker container executor service with no network, external judging, cgroups, and fail-closed safety. |
| [0011](0011-security-auth-session-and-judging-masking.md) | Auth Session Management, Outside-Sandbox Hardening & Judging Masking | 2026-10-20 | Accepted | Token revocation, refresh cookies, constant-time auth, tenant DEK derivation, hidden test masking, and rate limiting. |
| [0012](0012-persistent-skills-verbatim-feedback-and-hints.md) | Persistent Skill Map, Verbatim Feedback, Socratic Hints & Planly Preview | 2026-10-20 | Accepted | EMA user skills, transcript quote fidelity, three-tier hint ladder, and non-mutating plan adaptation preview. |
| [0013](0013-frontend-experience-and-design-system.md) | Frontend Experience, Design System, Monaco Workspace & Calibrated Analytics | 2026-10-20 | Accepted | Collapsible left rail, Cmd+K palette, Monaco split IDE, audio waveform presence, diverging delta charts, and Planly live preview. |
| [0014](0014-langchain-langgraph-agent-architecture.md) | LangChain + LangGraph Agent Architecture, Provider Preferences, Short-Term Memory & Evaluation | 2026-10-20 | Accepted | LangChain ChatBedrockConverse/MockChatModel, LangGraph stateful interview agent with sliding memory and Postgres checkpointing, task routing preferences, and question-level evaluation workflow. |
| [0015](0015-reliability-audit-turn-idempotency-and-grounded-evaluations.md) | Reliability Audit, Turn Idempotency, Memory Rolling, and Grounded Evaluations | 2026-10-20 | Accepted | Client turn idempotency, fail-closed checkpointer in prod, topic lifecycle memory rolling, unified model resolver, grounded evaluations, and frontend draft persistence. |
| [0016](0016-persistent-executor-learning-backlog-and-dsa-coaching.md) | Persistent Sandboxed Executor, User-Controlled Learning Backlog, Bedrock BYOC Onboarding, and Socratic DSA Coaching | 2026-10-20 | Accepted | Persistent Bubblewrap sandbox executor, BYOC least-privilege IAM policy generation, decoupled learning backlog from Planly schedules, and 4-tier on-demand DSA coaching. |
| [0017](0017-consolidated-bedrock-client-lifecycle-and-bounded-cache.md) | Consolidated Bedrock Client Lifecycle, Bounded LRU Cache, and Zero-Decryption Cache Hits | 2026-10-20 | Accepted | Consolidated ModelClientFactory/Resolver pipeline, zero DB/decryption on cache hit, bounded LRU/idle cache, config versioning, and atomic usage accounting. |
| [0018](0018-azure-openai-byoc-provider.md) | Azure OpenAI BYOC Provider for Student Accessibility | 2026-10-28 | Accepted | Extends BYOC architecture to Azure OpenAI Service (GPT-4o, GPT-4o-mini, Phi-3.5) with student friction reduction, dual-cloud onboarding, and billing warnings. |
| [0019](0019-cross-browser-cloud-neural-audio-tts-stt.md) | Cross-Browser Cloud Neural Audio Pipeline (TTS & STT) | 2026-11-02 | Accepted | Cloud neural TTS (Azure OpenAI, AWS Polly, Vaani, Edge Neural) and MediaRecorder STT for studio clarity and cross-browser parity in Firefox, Chrome, and Safari. |
| [0020](0020-tiered-company-tracks-enterprise-exam-and-retest-delta.md) | Tiered Company Career Tracks, Enterprise Hiring Exam Portal, and Closed-Loop Retest Engine | 2026-11-03 | Accepted | Gold/Silver/Bronze company tracks, multi-round enterprise exam runner with anti-cheating telemetry, Planly interactive calendar grid with .ics export, and closed-loop retest delta cards. |
| [0021](0021-roles-tenants-curated-simulations-and-anti-cheating.md) | Role-Based Access Control, Multi-Tenant Telemetry, 50+ Company Tracks, Placement Simulations, and Anti-Cheating Oral Cross-Examination | 2026-11-03 | Accepted | Candidate/recruiter/admin portals, real vs test cohort admin analytics, 52 community-curated company packs, 3-round placement simulations, and Stage 3 OA code cross-examination. |
| [0022](0022-explanation-checks-editor-telemetry-and-recruiter-replay.md) | Post-Code Explanation Checks, Editor Activity Telemetry & Recruiter Replay View | 2026-11-04 | Accepted | Grounded post-code cross-examination, sanitized keystroke telemetry with monotonic sequence ingestion, document delta reconstruction, 8 pure activity features, multi-family correlation flags, and recruiter replay view with product honesty notice. |
| [0023](0023-project-sandbox-hardening-and-server-side-prompt-log.md) | Project Test Sandbox Hardening & Server-Side Copilot Prompt Log | 2026-11-05 | Accepted | No host root mount, cleared env, JUnit-verified results against authoritative test names, static tamper scan, fail-closed without bubblewrap, editable-only overlay, and prompt scoring from a server-side copilot log. |
| [0024](0024-interview-turn-accounting-and-adaptive-policy.md) | Interview Turn Accounting & Deterministic Adaptive Policy | 2026-11-05 | Accepted | Message `kind` column, duration-based budget, follow-up cap and topic rotation enforced in code, intent handling, full prompt every turn, honest wrap-up, curated DSA problems, typed LLM errors. |
| [0025](0025-platform-voice-nova-sonic-hybrid.md) | Platform-Provided Voice: Nova 2.5 Sonic Hybrid | 2026-11-06 | Accepted (prototype) | Live voice via Bedrock bidirectional stream relay; engine decides every question through a tool; platform IAM role (no root keys); quotas; audio never stored; push-to-talk fallback. |

---


## ADR Process

1. Create a new markdown file named `NNNN-short-title.md`.
2. Follow standard ADR sections: Title, Date, Status, Context, Decision, Alternatives Considered, Rationale, Consequences & Trade-offs, Related Requirements.
3. Update this index.
4. When a past decision is modified, mark the previous record as `Superseded by NNNN` rather than rewriting historical records.
