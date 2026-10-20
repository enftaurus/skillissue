# ADR 0012 — Persistent Skill Map, Per-Question Verbatim Feedback, Socratic Hint Ladder, and Adaptive Rescheduling

- **Date**: 2026-10-20
- **Status**: accepted
- **Author**: Antigravity Staff Engineering Team

---

## 1. Context & Problem Statement

Skill Issue's core value proposition is:
```
Practice → Self-evaluate → Receive evidence-based feedback → Improve (Planly) → Reassess → Measure progress
```
Previously, post-interview evaluations generated summary scores, strengths, and weaknesses, but lacked question-by-question diagnostic depth. Candidates could not inspect exact verbatim quotes for each response, verify feedback grounding against transcripts, or receive calibrated hints during coding sessions without penalty ambiguity. Furthermore, user skill tracking was volatile across disparate sessions rather than accumulating into a persistent, mathematically sound skill mastery map.

## 2. Decision & Architecture

We have implemented the complete Phase 3 weakness loop with four core architectural components:

### 2.1 Persistent User Skill Map (`UserSkill` Model)
- **Table**: `user_skills` (`user_id`, `topic`, `score`, `confidence`, `last_seen`, `evidence_refs`).
- **Mathematical Update Rule**: Exponential Moving Average (EMA) with $\alpha = 0.3$:
  $$\text{score}_{t} = (1 - \alpha) \cdot \text{score}_{t-1} + \alpha \cdot \text{score}_{\text{observed}}$$
- **Confidence Tracking**: Increases with observation count ($\min(1.0, \text{confidence} + 0.1)$) and records typed evidence references (`evaluation`, `coding`, `plan_task`).
- **Omnipresent Loop Feeder**:
  1. Interview evaluations update rubric dimensions.
  2. Accepted coding problem submissions update algorithmic topics.
  3. Completed Planly tasks boost targeted technical skills.

### 2.2 Per-Question Verbatim Diagnostic Feedback
- Every interview evaluation now produces structured `question_feedback` objects containing:
  - `question_index`: Sequential question turn number.
  - `interviewer_question`: Exact prompt posed by the interviewer.
  - `candidate_answer`: Candidate explanation summary.
  - `verbatim_quote`: Substring extracted directly from the candidate transcript.
  - `critique`: Direct, dry, Gilfoyle-style technical analysis highlighting gaps or unverified claims.
  - `strong_answer_guide`: Concrete specification of what a staff-level answer covers.
  - `targeted_resource`: Recommended technical documentation or deep-dive article.
- **Backend Verification**: `EvaluationService` programmatically verifies that `verbatim_quote` exists in the candidate's transcript text. If the LLM generates a paraphrased or hallucinated quote, the system automatically falls back to the exact sentence uttered by the candidate in that turn, guaranteeing 100% quote fidelity.

### 2.3 Three-Tier Socratic Coding Hint Ladder
- DSA and coding interviews now feature calibrated Socratic hints accessed via `POST /api/v1/interviews/{interview_id}/hint`:
  - **Tier 1 (Nudge)**: Clarifying question or directional nudge (-5% penalty on `problem_solving_rigor`).
  - **Tier 2 (Pattern)**: Algorithmic pattern or optimal data structure identification (-15% penalty).
  - **Tier 3 (Structure)**: Concrete pseudocode or structural step-by-step logic (-30% penalty).
- Hint interactions are injected into the transcript with `[Requested Level {level} Hint]` and `[Level {level} Hint]: ...`.
- `interview.hint_level_used` tracks the highest hint level accessed and automatically applies calibrated deductions during post-interview evaluation.

### 2.4 Planly Reschedule Preview Engine
- Added `POST /api/v1/plans/{plan_id}/adapt/preview`:
  - Computes projected task shifts (`current_day` $\to$ `new_day`) and extended `new_total_days` (capped at 14 days) without mutating database state.
  - Allows candidates to preview the impact of falling behind before committing to the schedule change.

### 2.5 20 Golden Benchmark Dataset
- Expanded `scripts/run_benchmarks.py` to 20 comprehensive golden cases spanning Junior, Mid, Senior, and Staff levels across Technical, Behavioral, DSA, and Managerial categories.
- Benchmarks validate JSON schema conformity, verbatim quote transcript fidelity, and calibrated score bounds.

---

## 3. Security & Safety Invariants

1. **Transcript Grounding**: Verbatim quotes are strictly sanitized and checked against candidate input to prevent fabricated evidence.
2. **Untrusted Data Boundaries**: Interview transcripts and evaluation weaknesses remain enclosed in XML tags (`<untrusted_candidate_transcript>`, `<untrusted_evaluation_data>`) to block second-order prompt injection during evaluation and plan generation.
3. **User Isolation**: All `user_skills` queries and updates filter strictly on authenticated `user_id`.

---

## 4. Verification Evidence

- `backend/tests/`: 14/14 tests passing.
- `scripts/run_benchmarks.py`: 20/20 golden cases passing with 100% schema, quote fidelity, and score calibration.
- `scripts/sandbox_escape_suite.py`: 8/8 adversarial security tests passing.
