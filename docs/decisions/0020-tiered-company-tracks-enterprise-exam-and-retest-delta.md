# 0020. Tiered Company Career Tracks, Enterprise Hiring Exam Portal, and Closed-Loop Retest Engine

- **Date**: 2026-11-03
- **Status**: Accepted
- **Deciders**: Engineering Team, Product Owner

---

## Context

Skill Issue previously focused on generic domain mock interviews (System Design, Distributed Systems, Concurrency) and self-evaluations. However, real-world engineering students and recruiters requested key workflow evolutions:
1. **Targeted Company Career Tracks ("Mines")**: Students want company-specific interview problem tracks (Uber, Google, Amazon, Microsoft, Meta, Adobe, Atlassian, Swiggy, TCS Digital) reflecting genuine interview questions and community debriefs (sourced from Reddit and LeetCode Discuss), with 2–3 questions unlocked on Day 1 and progressive unlocking through practice.
2. **Personalized Planly Curriculum Calibration & Interactive Calendar**: Students required the ability to specify sprint duration (7, 14, 21, 30 days) and daily study commitment (30, 45, 60, 90, 120 mins) before curriculum synthesis, with pacing paced backward from their upcoming interview date, interactive day-by-day calendar grid, and one-click `.ics` export for Google Calendar / Apple Calendar.
3. **Closed-Loop Retest Engine & Score Delta**: After receiving evidence-backed diagnostic evaluations, students need a one-click mechanism to retest the identified weakness topic in a targeted 3-question adaptive session and receive verified Before vs After Score Delta cards ($+X\%$).
4. **Enterprise & Campus Hiring Exam Portal (`/enterprise`)**: College Training & Placement Officers (TPOs) and engineering recruiters need to configure multi-round candidate assessment pipelines (Round 1: Company DSA OA $\to$ Round 2: AI Take-Home Project $\to$ Round 3: Anti-Sycophancy AI Technical Interview $\to$ Round 4: Google Code Comprehension [Coming Soon]). Candidates take continuous exams via unique token-gated sessions (`/assess/take/:token`) with anti-cheating telemetry (window blur/tab-switch count, copy-paste count, speech vs code divergence flag), feeding into a real-time recruiter leaderboard.
5. **Observability & Funnel Telemetry (`/admin/funnel`)**: Need high-level observability into student activation funnel conversion rates and provider reliability.

---

## Decisions

### 1. Tiered Company Career Tracks Module (`backend/app/tracks/`)
- Seeded company tracks partitioned into **Gold, Silver, and Bronze Mines**:
  - Gold: Uber, Google, Meta
  - Silver: Amazon, Microsoft, Atlassian
  - Bronze: Adobe, Swiggy, TCS Digital
- Community debriefs curated from candidate interview reports (Reddit, LeetCode Discuss) without exposing external repo links.
- Day-1 access: Exactly 3 high-frequency questions unlocked by default (`is_initially_unlocked = True`); subsequent questions unlock progressively as prior problems are solved.
- Sandboxed code execution reusing the isolated runner.

### 2. Planly Calendar Grid & Pre-Generation Configuration
- Enhanced `POST /api/v1/plans/generate/{evaluation_id}` to accept `GeneratePlanFromEvaluationRequest(total_days, daily_study_minutes, target_date)`.
- UI provides a pre-generation configuration modal allowing students to select duration (7, 14, 21, 30 days) and study time (30, 45, 60, 90, 120 mins).
- View switcher between Sprint Timeline and Calendar Grid with day boxes, task chips, checkboxes to toggle completion, and interview countdown banner.
- Standard RFC 5545 iCalendar `.ics` file generator for one-click export to Google Calendar and Apple Calendar.

### 3. Closed-Loop Retest Engine & Before/After Score Delta (`backend/app/evaluations/`)
- `RetestSession` database model and API routes:
  - `POST /api/v1/evaluations/{id}/retest`: provisions focused 3-question adaptive retest interview on the identified weakness topic.
  - `GET /api/v1/evaluations/{id}/retests`: returns retests and score delta records.
  - `POST /api/v1/evaluations/retests/{id}/complete`: computes before/after score delta and extracts verified improvements.
- Evaluation report UI displays prominent "Retest Weakness" action button on every diagnostic weakness card and renders the Verified Progress & Score Delta card with before vs after scores, delta badge ($+X\%$), and verified mastery evidence.

### 4. Enterprise & Campus Hiring Exam Portal (`backend/app/enterprise/`)
- Recruiter Job Description (JD) uploader and assessment pipeline configurator supporting multi-round pipelines:
  - Round 1: OA DSA Coding
  - Round 2: AI Take-Home Project (Read-Only AI Copilot)
  - Round 3: Anti-Sycophancy AI Technical Interview
  - Round 4: Google Code Comprehension (Coming Soon)
- Public token-gated candidate assessment runner (`/assess/take/:token`):
  - Focus Mode hiding sidebar navigation and external links.
  - Active browser event listener (`window.addEventListener('blur')`) tracking tab switching and focus loss.
  - Round submission handler capturing code answers, speech answers, and integrity telemetry.
- Recruiter Cohort Leaderboard (`/enterprise`):
  - Ranks candidates by composite score with window blur flags and status tracking.

### 5. Admin Funnel & Observability Telemetry (`backend/app/analytics/`)
- `GET /api/v1/analytics/funnel` computes user conversion funnel:
  $\text{Signups} \to \text{First Interview} \to \text{Evaluation Viewed} \to \text{Planly Plan Created} \to \text{Retest Completed}$.
- Frontend dashboard (`/admin/funnel`) displays step-by-step conversion rates, drop-off percentages, and audio/inference provider health indicators.

---

## Consequences & Trade-offs

### Positive
- **Closed Loop**: Direct connection between evaluation diagnostics, personalized Planly calendars, and verified retest score improvements.
- **Enterprise & Campus Placements**: Provides colleges and recruiters with an automated, cheat-resistant assessment pipeline without requiring students to create external AWS accounts.
- **Community Grounded**: Sourced high-frequency interview questions tailored to specific tech giants.
- **Calendar Integration**: Students can import their Planly schedule directly into their personal calendar apps.

### Considerations
- Anti-cheating window blur signals are client-reported; in enterprise high-stakes environments, proctoring should combine client blur telemetry with LLM response entropy and speech/code divergence checks.
