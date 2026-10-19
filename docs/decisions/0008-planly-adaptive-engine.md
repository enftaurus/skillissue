# ADR 0008: Planly Adaptive Learning Engine

- **Date:** 2026-10-20
- **Status:** Accepted
- **Context:** Practice without targeted follow-up fails to produce long-term retention. Students need structured, multi-day roadmaps customized to their exact demonstrated weak areas.
- **Decision:** Build Planly as an adaptive improvement engine that ingests rubric gap outputs from evaluations, takes into account candidate daily study time (e.g. 30, 45, 60 minutes), and generates daily bite-sized tasks with curated external resources (documentation, practice questions). The engine dynamically adjusts schedules when a candidate misses days or demonstrates mastery in reassessments.
- **Alternatives Considered:**
  - *Static checklist*: Rejected because static checklists ignore individual time constraints and performance variance.
  - *Full AI-generated video/course curriculum*: Rejected per PRD non-goals to prevent information bloat and maintain focus on concise practice tasks.
- **Rationale:** Bite-sized tasks connected directly to evidence quotes empower the student to tackle one conceptual gap at a time.
- **Consequences:** Tasks and plans are versioned entities in PostgreSQL, linked to evaluations and reassessment attempts.
- **Related Requirements:** PRD FR-11; Master Prompt Section 9.
