# 0024. Interview Turn Accounting & Deterministic Adaptive Policy

- **Status**: Accepted
- **Date**: 2026-11-05
- **Deciders**: QA / Interview Engine
- **Consulted**: Product

---

## Context

The 2026-11-05 QA audit showed that, with a real LLM (Azure gpt-4.1-mini), the LangGraph interviewer:

- Never left the first topic: 9 follow-ups about Redis in a Python/FastAPI/PostgreSQL interview. The LLM decision path had no follow-up cap; the deterministic fallback that rotates topics only runs when the LLM call fails, which is all the tests ever exercised.
- Reworded the same question after "idk", ignored "can you repeat the question?", and asked compound questions.
- Ended every session with "Thank you for your concrete explanations", even after "asdfgh" and "bye".
- Counted code Runs, hint requests and repeat requests as candidate answers. It allowed 9 answers instead of 8 (the collection was stale), and it ignored the chosen duration.
- Dropped company/JD/resume context and the untrusted-data rules after turn 1 (the "lean prompt").
- Re-presented the DSA problem once it slid out of the 6-message window, and auto-picked Codeforces stubs with no statement and empty tests.

## Decision

1. **`interview_messages.kind`** (migration `0016`). User kinds: `answer | code_submit | code_run | hint_request | meta`. Assistant kinds: `question | hint | code_feedback | repeat | wrapup`. Only `answer` and `code_submit` consume the budget. Grouped transcripts pair questions and answers chronologically and skip hint/repeat exchanges.
2. **Budget from duration**: `max_turns = max(4, round(minutes * 0.4))`, so 15 → 6, 20 → 8, 30 → 12 answers. Only the budget ends an interview; an LLM `wrapup` suggestion or candidate text cannot.
3. **Deterministic policy after the LLM suggestion** (`backend/app/interviews/agent/policy.py`): at most 2 follow-ups per topic, then rotate to the next unstarted or least-probed skill. The first non-answer gets a simpler question; the second moves on at lower difficulty. Intents (`repeat_question`, `clarify`, `asks_for_solution`, `injection`, `concept_question`) are classified in code. Repeat and clarify are answered without an agent turn and don't count.
4. **Prompt hygiene**: the full system prompt (company calibration, JD, resume, untrusted-data rules) plus per-turn rules on every turn. All candidate text is wrapped in `<untrusted_candidate_answer>`. Output is reduced to a single question, and a near-duplicate of the previous question triggers one regeneration.
5. **Honest wrap-up** built from the per-answer quality log.
6. **DSA**: a persisted `problem_presented` flag. The problem statement is appended verbatim by code; the LLM only writes the acknowledgement. Interviews auto-pick from curated problems with real tests, and the judge refuses problems with no runnable tests (`PROBLEM_NOT_JUDGEABLE`). The brute-force detector is indentation-aware.
7. **Errors**: LLM failures map to typed errors (`MODEL_CONTENT_FILTERED` 422, `MODEL_RATE_LIMITED` 429, `MODEL_TIMEOUT` 504, `MODEL_UNAVAILABLE` 502). The failed answer is rolled back and the checkpoint restored. The checkpointer context manager no longer wraps `yield`, so body exceptions aren't mistaken for connection failures.

## Consequences & Trade-offs

- More tokens per turn (the full system prompt every turn). gpt-4.1-mini cost stays in the cents per interview, and prefix caching applies to the stable system prompt.
- Regex intent classification can misfire on unusual phrasing. The LLM suggestion still drives normal answers, and misclassification fails safe (simpler question, no turn consumed).
- Rubric percentages now map 1-5 to 0-100 (`(s-1)/4`), so new scores are not directly comparable with older ones (floor 20 → 0).
