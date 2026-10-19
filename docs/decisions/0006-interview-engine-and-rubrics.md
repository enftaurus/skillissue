# ADR 0006: Unified Interview Engine & Post-Interview Evaluation

- **Date:** 2026-10-20
- **Status:** Accepted
- **Context:** Interviews can be initiated either by choosing target domains/skills or by uploading/pasting a Job Description. In both cases, the interview flow, evaluation criteria, and learner progress tracking must remain unified.
- **Decision:** Build a single shared interview engine that dynamically configures its question scope from either Domain skills or parsed JD requirements. Execute candidate self-evaluation first, followed by a separate, dedicated AI evaluation pass against explicit rubric criteria.
- **Alternatives Considered:**
  - *Separate engines for JD and Domain modes*: Rejected because code duplication would make rubric scoring and progress analytics inconsistent.
  - *Grading inside the interview conversation turn*: Rejected because inline grading creates bias, distracts the conversational interviewer persona, and impairs evaluation rigor.
- **Rationale:** A dedicated post-interview evaluation pass allows the evaluator model to inspect the entire transcript holistically, cite direct excerpts as evidence, compare against candidate self-ratings, and generate calibrated gap analyses.
- **Consequences:** The system maintains two model prompt strategies: one conversational interviewer prompt (single questions, natural tone, adaptive follow-ups) and one analytical evaluator prompt (strict JSON schema, rubric scoring, evidence citation).
- **Related Requirements:** PRD FR-03, FR-04, FR-07, FR-08; Master Prompt Section 4, 9, 10.
