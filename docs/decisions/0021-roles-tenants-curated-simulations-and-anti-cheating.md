# 0021. Role-Based Access Control, Multi-Tenant Telemetry, 50+ Company Tracks, Placement Simulations, and Anti-Cheating Oral Cross-Examination

- **Date**: 2026-11-03
- **Status**: Accepted
- **Deciders**: Engineering Team, Product Owner

---

## Context

Following user feedback and requirements for campus placement and enterprise recruitment readiness, Skill Issue required core architectural enhancements:
1. **User Role Separation & Portal Isolation**:
   - Distinct portals for `candidate` (`/login`), `recruiter` (`/enterprise/login`), and `admin` (`/admin/login`).
   - Candidate view must strictly conceal recruiter and admin capabilities (e.g. candidate assessment pipeline management, enterprise dashboards, system analytics).
2. **50+ Curated Company Career Packs & Placement Simulations**:
   - Expand beyond initial company tracks to 50+ top global and Indian tech firms (Google, Uber, Meta, Amazon, Microsoft, Apple, Netflix, OpenAI, Stripe, Databricks, ByteDance, Swiggy, Zomato, PhonePe, Flipkart, Meesho, etc.).
   - Curate problems from real community experiences (LeetCode Discuss, Reddit, Glassdoor) with strict Day-1 unlock rules (2–3 questions unlocked on Day 1, progressive unlocks with practice).
   - Flagship Placement Simulations (3-round full company placement drives: Google SDE, Uber Backend Systems, OpenAI AI Systems).
3. **Anti-Cheating Oral Cross-Examination**:
   - In enterprise multi-round assessments, candidates often copy-paste OA DSA solutions or use unauthorized aids.
   - Stage 3 oral technical interviewer must actively cross-examine the candidate on their exact submitted Round 1 OA code (`oa_submitted_code`), probing data structure selection, Big-O trade-offs, and edge case handling.
4. **Multi-Tenancy & Isolated Admin Analytics (`/admin/analytics`)**:
   - Platform needs `Tenant` data isolation separating real production candidate cohorts from internal QA mock/test sandbox users (`is_test = True`).
   - Admin Analytics must provide partitioned telemetry for Real vs Test Sandbox cohorts, reporting activation KPIs, average interview durations, dimension breakdowns, recurring weakness topics, and registered tenant organizations.
5. **Progress Page Crash Elimination**:
   - The `/progress` page previously suffered white screens due to missing null-checks on nested analytics fields when rendering skill graphs, reassessments, dimension trends, and recurring weaknesses.

---

## Decisions

### 1. Multi-Tenant Role-Based Access Control (`backend/app/database/models.py`)
- Created `Tenant` model (`id`, `name`, `slug`, `tier`, `created_at`).
- Added `role` enum (`candidate`, `recruiter`, `admin`), `tenant_id` foreign key, and `is_test` boolean flag to `User`.
- Added `oa_config` JSON to `AssessmentPipeline` to support customizable OA specifications.
- Added `resume_text`, `oa_problem_title`, and `oa_submitted_code` to `CandidateAssessment` for auditability and proctoring cross-examination.
- Implemented role-based dependencies (`get_current_recruiter_user`, `get_current_admin_user`) in `backend/app/auth/dependencies.py`.

### 2. Curated 50+ Company Registry & Placement Simulations (`backend/app/tracks/company_registry.py`)
- In-memory structured registry of 52 tech companies across Gold, Silver, and Bronze mines, each containing 5 questions curated from candidate community experiences with exactly 2–3 questions unlocked on Day 1.
- Implemented 3 Flagship Placement Simulations:
  - **Google Software Development Engineer (L3/L4)**: Round 1 OA (Stream Processing & Sliding Window), Round 2 Machine Coding (In-Memory Key-Value Store with TTL & Compaction), Round 3 Oral Interview (Google scale & concurrency).
  - **Uber Software Engineer (Backend & Systems)**: Round 1 OA (Geohash Spatial Driver Dispatch Index), Round 2 Machine Coding (Real-Time Driver Location Service), Round 3 Oral Interview (Uber high-throughput distributed systems).
  - **OpenAI AI Engineer (AI Systems & Scaling)**: Round 1 OA (KV Cache Paged Attention Memory Allocation), Round 2 Machine Coding (Chunked Batch Inference Queue with Streaming Tokens), Round 3 Oral Interview (OpenAI inference optimization & scaling).
- Implemented Google Code Comprehension Beta tab.

### 3. Anti-Cheating Oral Technical Cross-Examination (`backend/app/interviews/prompts.py`)
- When an enterprise candidate enters Round 3, `oa_submitted_code` and `oa_problem_title` are dynamically injected into the interviewer's system prompt.
- The interviewer asks targeted follow-ups challenging the candidate's exact code choices, time/space complexity, and invariant guarantees, identifying disconnects between written code and oral explanation.

### 4. Recruiter Candidate Audit Modal & OA Customizer (`frontend/src/features/enterprise/`)
- Recruiter portal allows selecting OA questions from Curated Presets, custom LeetCode/Codeforces problem URLs, or dynamic Codeforces problem selection by rating (800–2400) and topic tag.
- Recruiter Candidate Audit modal surfaces candidate resume text, round-by-round score breakdown, anti-cheating signals (window blurs, copy-pastes, audio divergence flag), and full submitted OA code snippet.

### 5. Multi-Tenant Admin Analytics & Partitioned Telemetry (`backend/app/analytics/`)
- `GET /api/v1/analytics/admin/stats` calculates isolated telemetry metrics for Real vs Test Sandbox cohorts:
  - Total users, active candidates, interviews completed, candidate average score, mean duration, and drop-off rate.
  - Dimension breakdown (Technical Depth, Problem Solving, Communication, Systems Architecture) and recurring weaknesses.
  - Registered tenant list with user counts.
- Dedicated frontend Admin Analytics dashboard at `/admin/analytics` with Real vs Test Sandbox tab toggle.

### 6. Progress Analytics Null-Safety Hardening (`frontend/src/features/progress/ProgressAnalyticsPage.tsx`)
- Guarded all nested accessors (`dimension_trends`, `recurring_weaknesses`, `skill_graph`, `reassessments`) with optional chaining and empty state defaults (`[]`), eliminating runtime render exceptions.

---

## Consequences & Trade-Offs

- **Security & Privacy**: Candidate code and resume text are stored scoped to the recruiter's tenant. Candidates cannot view internal evaluation notes or other candidates' data.
- **In-Memory Registry Performance**: Maintaining 52 companies in `company_registry.py` eliminates database bloat and migration overhead for static problem catalogs, while dynamic progress tracking remains normalized in PostgreSQL.
- **Fairness & Anti-Cheating**: Cross-examining candidates on their exact OA submissions dramatically reduces false positive hires from external assistance without requiring intrusive biometric surveillance software.
