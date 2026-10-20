# ADR 0015: Reliability Audit, Turn Idempotency, Memory Rolling, and Grounded Evaluations

- **Status**: Accepted
- **Date**: 2026-10-20
- **Authors**: Staff Software Engineer, Backend Architect, Application Security Engineer

## Context

Prior to this reliability audit:
1. Interview message delivery had race conditions during network retries; double clicks or retry storms could spawn duplicate assistant turns.
2. The LangGraph checkpointing fallback in production could degrade silently to memory when Postgres failed, risking state loss.
3. Conversational memory relied on ad-hoc regex/keyword detection (e.g. searching for "redis", "10x", "paxos") to trigger transitions rather than rubric-driven topic lifecycles.
4. Evaluation quote extraction occasionally extracted quotes across different questions or attributed unrelated candidate answers.
5. Provider resolution was bifurcated between `ModelFactory` and `ModelClientFactory`, risking configuration drift and silent fallback masking.
6. Frontend forms and editors lacked input draft persistence and retry ergonomics, using raw `alert()` dialogues and optimistic UI without failure rollback.

## Decision

1. **Client Turn Idempotency & Database Row-Level Locking**:
   - Added `client_turn_id` column to `interview_messages` with database migration `0005_turn_id_and_topic_status`.
   - In `backend/app/interviews/service.py`, message handling uses `select(InterviewMessage).where(InterviewMessage.client_turn_id == client_turn_id)` under row locking to reject or replay duplicates deterministically.
   - Guarded against concurrent message dispatches while an existing turn is active.

2. **Fail-Closed Checkpointer in Production**:
   - In `backend/app/interviews/agent/checkpoint.py`, if Postgres checkpointer initialization or persistence fails in production environments, the system raises `AppException("CHECKPOINT_PERSISTENCE_FAILED", status_code=503)` rather than silently degrading to in-memory state. In development/testing, an explicit warning is logged when falling back to memory.

3. **Topic Lifecycle & Rolling Conversational Memory**:
   - Removed all superficial keyword heuristic matching.
   - Introduced explicit `topic_statuses` tracking rubric topics across states (`unaddressed` -> `probing` -> `evaluated` -> `completed`).
   - Integrated a sliding 6-turn rolling conversation window in agent state, coupled with candidate evidence linked to message IDs.
   - Added GET `/api/v1/interviews/{id}/state` endpoint for transparency.

4. **Unified Provider & Model Resolution**:
   - Centralized model resolution in `backend/app/providers/resolver.py` (`ModelResolver.resolve`).
   - Standardized `ModelResolutionResult` reporting `active_provider`, `model_id`, `is_fallback`, `fallback_reason`, and `requested_provider`.
   - Refactored both `ModelFactory` and `ModelClientFactory` to delegate to this shared resolver.

5. **Grounded Question Evaluations & Idempotent Skill Updates**:
   - In `backend/app/evaluations/service.py`, verbatim quotes are extracted strictly from candidate answers belonging to that specific turn index (`grouped_by_idx[q_idx]`), preventing cross-question hallucination.
   - User skill EMA updates are indexed by evaluation ID and dimension to prevent double-application on duplicate submission.
   - Deterministic delta computation `score_gap = q_ai_score - q_self_score`.

6. **Frontend Reliability & Draft Persistence**:
   - Retained message draft in text area on network/API failure and rolled back optimistic assistant bubble.
   - Added retry capabilities with `client_turn_id`.
   - Preserved coding editor state per problem and language in `localStorage`.
   - Preserved self-evaluation ratings and reflections in `sessionStorage`.
   - Replaced all raw browser `alert()` invocations with accessible inline status banners and toast messages.

## Consequences & Trade-offs

- **Pros**:
  - Predictable turn-by-turn conversation flow without duplicate responses.
  - Verifiable evidence quotes with zero hallucination outside the turn response.
  - Fail-closed production durability without silent state loss.
  - Robust frontend UX that preserves user work across failures and network drops.
- **Cons**:
  - `client_turn_id` requires client support (handled transparently by UUID generation in frontend API calls).
  - Production checkpointing requires accessible Postgres instance.
