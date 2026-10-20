# LangChain + LangGraph Migration & Architecture Assessment

- **Date**: 2026-10-20
- **Scope**: Interview Orchestration, Conversational Memory, Multi-Provider Preferences, Structured Post-Interview Evaluation
- **Target Stack**: LangChain Core (`langchain-core>=1.6`), LangGraph (`langgraph>=1.2`), `langgraph-checkpoint-postgres`, AWS Bedrock Converse (`langchain-aws`), FastAPI, PostgreSQL 16.

---

## 1. Current State vs. Target Architecture

### Current State
- Model calls are made via a custom `BaseProvider` class (`AmazonBedrockProvider`, `MockProvider`) with direct boto3 calls.
- Interview turns are executed sequentially via single prompt generation in `InterviewService.send_message` with raw conversational history array.
- Turn decisions (whether to follow up or move on) rely purely on prompt instructions without explicit graph routing or typed state transitions.
- Checkpoints are not stored in LangGraph; session state resides in the relational `interviews` and `interview_messages` tables.
- Model selection is single-preference (`preferred_model` in `ProviderConfig`) rather than task-specific (interviewer, evaluator, coder).
- Evaluation is executed in one monolithic post-interview prompt rather than a multi-stage evidence extraction and calibration pipeline.

### Target Architecture
1. **LangChain Model Client Integration**:
   - Universal LangChain `BaseChatModel` interface across all providers.
   - `ChatBedrockConverse` wrapping Amazon Bedrock Converse API with credentials decrypted only in memory per request.
   - `MockChatModel` providing complete zero-cost offline development and deterministic test execution.
   - `ModelClientFactory` resolving per-user task-specific preferences (`interviewer`, `evaluation`, `coding`, `planning`).

2. **LangGraph Stateful Interview Agent**:
   - Explicit typed state: `InterviewAgentState` tracking phase, recent conversational window, running summary, covered topics, current difficulty, and pending follow-ups.
   - Stateful nodes: `load_state`, `prepare_context`, `assess_candidate_turn`, `generate_question`, `persist_turn`, `wrapup_interview`.
   - Conditional edges implementing adaptive questioning (probe unverified claims, increase difficulty on solid answers, change topic when covered, wrap up on budget).
   - PostgreSQL-backed checkpointing via `AsyncPostgresSaver` scoped to `interview_{interview_id}`.

3. **Memory & Context Management**:
   - Bounded recent conversational window (last 6 turns) prevents context window exhaustion.
   - Running interview summary captures verified candidate claims, demonstrated skills, and open questions without duplicating the entire transcript.

4. **Structured Post-Interview Evaluation & Reflection**:
   - Question-grouped transcript presentation.
   - Per-question candidate self-evaluation (1–5 scale, strengths, missed points, confidence).
   - Logically separate evaluation pipeline assessing answers with versioned rubrics and verbatim transcript evidence.
   - Deterministic score aggregation (question scores, dimension scores, overall score).
   - Self vs. AI divergence comparison (`ai_score - self_score`) with explanation.

---

## 2. Component Assessment & Retain/Refactor Matrix

| Component | Disposition | Strategy |
|---|:---:|---|
| `AuthService` & JWT Token Versioning | **Retain** | Full reuse; all queries filter by authenticated `user_id`. |
| `sandbox/` & Ephemeral Docker Microservice | **Retain** | Full reuse; completely isolated from LLM agent orchestration. |
| `backend/app/providers/` | **Refactor** | Wrap with `ModelClientFactory` returning LangChain `BaseChatModel` (`ChatBedrockConverse`, `MockChatModel`). |
| `backend/app/interviews/` | **Refactor** | Evolve `InterviewService` to invoke stateful `InterviewAgent` powered by LangGraph with PostgreSQL checkpointing. |
| `backend/app/evaluations/` | **Refactor** | Add per-question self-evaluation, evidence extraction, deterministic scoring, and divergence comparison. |
| `PlanlyService` & `UserSkill` EMA | **Retain** | Feed validated skill gaps from post-interview evaluations directly into Planly and Persistent Skill Map. |
| Database Tables | **Extend** | Add task-specific model preferences to `provider_configs`; add question-level evaluations to `self_evaluations`. |

---

## 3. Backward Compatibility & Safety Invariants

1. **Zero Secret Leaks**: Decrypted AWS credentials exist only in memory during model client invocation; never saved in LangGraph state or Postgres checkpoints.
2. **Offline Development**: If no credentials exist or `provider="mock"`, `MockChatModel` runs seamlessly without internet or cloud billing.
3. **User Isolation**: All checkpoints, transcripts, and preferences are strictly isolated by `user_id`.
4. **Idempotency**: Retried message submissions or duplicate evaluation requests do not create duplicate messages or corrupt state.
