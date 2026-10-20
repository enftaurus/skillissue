# ADR 0014: LangChain + LangGraph Agent Architecture, Provider Preferences, Short-Term Memory & Question-by-Question Evaluation

- **Status**: accepted
- **Date**: 2026-10-20
- **Author**: Staff AI Systems & Backend Architect

---

## 1. Context

Skill Issue is an AI-powered interview preparation platform. The core user loop is:
```
Practice → Self-evaluate → Receive evidence-based feedback → Improve (Planly) → Reassess → Measure progress
```

Prior to this decision, the interview engine used direct, single-turn LLM calls. While functional, it had several architectural limitations:
1. **Stateless Conversational Flow**: Context was managed solely by concatenating previous raw database messages, which caused token bloat on long interviews and lacked structured state transitions.
2. **Coarse Model Selection**: Users could only pick a single global model for all tasks, preventing optimal cost/quality specialization (e.g. using Qwen3 32B for dynamic interviewing, Qwen3 Coder for technical programming hints, and Qwen3 Next 80B for nuanced rubric evaluation).
3. **Absence of Adaptive Orchestration**: The interviewer lacked an explicit decision graph to decide whether to press with an adaptive follow-up, switch topics, modulate difficulty, or wrap up the session.
4. **Coarse Evaluation Reflection**: Post-interview evaluations were captured primarily at the high-level rubric dimension scale, without structured question-by-question candidate self-evaluations and side-by-side answer comparisons.

---

## 2. Decision

We evolved the interview engine into a **provider-configurable LangChain + LangGraph agent architecture** with PostgreSQL-backed short-term memory and structured question-level evaluation:

### 2.1 LangChain Chat Model Abstraction & ModelClientFactory
- Adopted LangChain's `BaseChatModel` standard.
- Integrated `ChatBedrockConverse` from `langchain-aws` for live Amazon Bedrock inference, passing credentials decrypted in ephemeral memory using tenant DEK keys (`decrypt_secret`).
- Implemented `MockChatModel` in `backend/app/providers/mock_chat_model.py` inheriting from `BaseChatModel`, providing deterministic structured outputs (`with_structured_output(AdaptiveDecision)`) and realistic offline dialogue with zero network requirements.
- Centralized model resolution in `ModelClientFactory.get_chat_model(db, user_id, task_type)` with support for task-specific routing:
  - `task_type="interviewer"`: Resolves `interviewer_model` (default: Qwen3 32B).
  - `task_type="evaluation"`: Resolves `evaluation_model` (default: Qwen3 Next 80B).
  - `task_type="coding"`: Resolves `coding_model` (default: Qwen3 Coder 30B).
  - `fallback_enabled`: Automatically routes to configured fallback provider/model upon errors or timeouts.

### 2.2 Stateful LangGraph Interview Agent (`backend/app/interviews/agent/`)
- **State Schema (`InterviewAgentState`)**: TypedDict tracking `interview_id`, `user_id`, `category`, `target_role`, `difficulty`, `domain_skills`, `current_topic`, `covered_topics`, `running_summary`, `recent_messages` (bounded to last 6 turns), `candidate_evidence`, `turn_count`, `max_turns` (8), and `next_action`.
- **Node Pipeline**:
  - `prepare_context_node`: Prunes conversation history to a sliding window of the last 6 turns and compresses older conversational turns into a running summary.
  - `assess_candidate_turn_node`: Invokes the model with structured output (`AdaptiveDecision`) to categorize candidate answers (complete, partial, vague, incorrect) and select `next_action` (`ask_follow_up`, `next_topic`, `increase_difficulty`, `decrease_difficulty`, `wrapup`).
  - `generate_question_node`: Constructs calibrated prompts enforcing single-question discipline, skeptical probing, and short responses without praise.
  - `wrapup_interview_node`: Generates a professional closing message and sets session phase to `completed`.
- **Checkpointing (`get_interview_checkpointer`)**: Uses `AsyncPostgresSaver` connected to the local PostgreSQL database, with seamless fallback to `MemorySaver` in isolated unit test sessions.

### 2.3 Question-by-Question Evaluation & Deterministic Scoring
- Added `GET /api/v1/interviews/{id}/transcript/grouped` returning structured `QuestionTurn` pairs (interviewer question, candidate answer, message IDs).
- Extended `SelfEvaluationCreate` and `self_evaluations` database table with `question_evaluations` JSON containing question index, score (1–5), self-identified strengths, missed points, and confidence.
- Reconciled `overall_score` in `EvaluationService.generate_ai_evaluation` deterministically in Python as the weighted average of the rubric dimensions, preventing model arithmetic hallucinations.
- Enhanced `EvaluationService.get_comparison` to produce `question_comparisons` aligning candidate question self-scores with AI verbatim quotes, critiques, and model answer guides.

### 2.4 Frontend Integration
- **Provider Settings (`ProviderSettingsPage.tsx`)**: Added controls for Task-Specific Routing (Interviewer, Evaluator, Coding Specialist), Fallback toggle & fallback model, and inference parameters (Temperature slider, Max Tokens input).
- **Self-Evaluation Modal (`SelfEvaluationModal.tsx`)**: Added tabbed navigation allowing candidates to evaluate both high-level rubric dimensions and per-question turns before triggering AI evaluation.
- **Evaluation Report (`EvaluationPage.tsx`)**: Enriched the Per-Question Verbatim Feedback accordion with candidate self-scores, self-identified strengths, missed points, and AI critiques side-by-side.

---

## 3. Database Migration

Applied migration `0004_provider_prefs_memory.py`:
- `provider_configs`: Added `default_model`, `interviewer_model`, `evaluation_model`, `coding_model`, `planning_model`, `fallback_enabled`, `fallback_provider`, `fallback_model`, `temperature`, `max_tokens`.
- `interviews`: Added `current_summary` (Text) and `covered_topics` (JSON).
- `self_evaluations`: Added `question_evaluations` (JSON).

---

## 4. Verification & Testing Evidence

1. **Backend Test Suite**:
   - `PYTHONPATH=. backend/venv/bin/pytest backend/tests -v`
   - **Result**: 15/15 tests passing in 9.84s (including `test_langgraph_interview_agent.py`).
2. **Evaluator Quality Benchmarks**:
   - `PYTHONPATH=. backend/venv/bin/python3 scripts/run_benchmarks.py`
   - **Result**: 20/20 benchmark cases evaluated successfully with 100% calibration, verbatim fidelity, and score bounds.
3. **Adversarial Sandbox Security**:
   - `PYTHONPATH=. backend/venv/bin/python3 scripts/sandbox_escape_suite.py`
   - **Result**: 8/8 sandbox security tests passing (non-root UID 10001, zero network access, canary file isolation, seccomp filters, 25 concurrent submissions).
4. **Frontend TypeScript & Vite Build**:
   - `npm --prefix frontend run build`
   - **Result**: Zero TypeScript errors, bundled in 2.61s.
