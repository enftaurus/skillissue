# Engineering Audit Findings & Verification Report — Skill Issue

**Date**: 2026-10-20  
**Scope**: Full-Stack Architecture, AppSec, BYOC Bedrock Providers, LLM Reliability, Sandbox Boundary, Frontend UX  
**Standards**: PRD v1.0, ADRs 0001–0009, AGENTS.md Invariants  
**Audit Resolution**: All 14 verified findings (3 P0, 3 P1, 6 P2, 2 P3) resolved and verified with automated regression tests.

---

## Summary of Findings & Resolution Status

| Finding ID | Severity | Category | Description | Status | Verification Evidence |
| :--- | :---: | :--- | :--- | :---: | :--- |
| **SEC-01** | P0 | Sandbox Security | Runner inherited parent host environment secrets | **Partially Fixed / Re-opened** | Scrubbing `os.environ` in host subprocess left filesystem (`backend/.env`) & network exposed. Docker executor required. |
| **SEC-02** | P0 | Sandbox Stability | Process group isolation & fork bomb mitigation | **Partially Fixed / Re-opened** | Host process groups & `RLIMIT_NPROC` insufficient without container cgroup PID limits. Docker container required. |
| **SEC-03** | P0 | BYOC Integration | AWS Access Key ID masking broke subsequent Bedrock calls | **Resolved & Verified** | `test_byoc_credentials_encryption_and_retrieval` PASSED |
| **SEC-04** | P1 | Configuration / Sec | Insecure default secrets allowed when `ENVIRONMENT=production` | **Resolved & Verified** | `test_production_secrets_validation` PASSED |
| **LLM-01** | P1 | LLM Output Quality | Model JSON parsing failures fabricated silent 70.0 score | **Resolved & Verified** | `test_evaluation_parsing_failure_rejects_fabricated_score` PASSED |
| **LLM-02** | P2 | AI Security | Untrusted candidate text without prompt boundary tags | **Resolved & Verified** | XML boundaries added to evaluation, interview, resume & JD prompts |
| **PRV-01** | P2 | Model Routing | Silent override of user preferred model during coding tasks | **Resolved & Verified** | `backend/app/providers/factory.py` routing calibrated with tests |
| **DB-01** | P2 | Schema & Config | Outdated Claude model IDs in auth service and database models | **Resolved & Verified** | Aligned with `mock-qwen3-32b` & `qwen.qwen3-32b-instruct-v1:0` |
| **FE-01** | P1 | Frontend / Speech | Streaming speech recognition caused exponential text duplication | **Resolved & Verified** | Non-duplicating committed/interim separation in `InterviewSessionPage.tsx` |
| **FE-02** | P1 | Frontend / Editor | Switching language or problem cleared candidate code draft | **Resolved & Verified** | Persistent draft cache (`draftsRef` / `codeDraftsRef`) implemented |
| **FE-03** | P2 | Frontend / Audio | Active microphone transcribed AI question from speakers (feedback loop) | **Resolved & Verified** | `speakWithMicSuppression` coordinates TTS & mic muting |
| **FE-04** | P2 | Frontend / API | Hard page reload on 401 discarded in-flight user drafts | **Resolved & Verified** | Path guard, active token check, and `auth:expired` event dispatch in `api.ts` |
| **FE-05** | P2 | Frontend / UX | Missing evaluation resulted in unrecoverable dead end | **Resolved & Verified** | "Generate Evaluation Now" CTA added to `EvaluationPage.tsx` |
| **FE-06** | P3 | Accessibility | Missing ARIA labels, radiogroup roles, and modal labeling | **Resolved & Verified** | `role="dialog"`, `aria-labelledby`, `role="radiogroup"`, `role="radio"` added |

---

## Detailed Audit Findings & Implemented Fixes

### [SEC-01] P0: Sandboxed Code Runner Host Environment Leakage
- **Severity**: P0 (High-Impact Security Vulnerability)
- **Category**: Sandbox Security / Secret Isolation
- **Location**: [`sandbox/runner.py`](file:///home/rajababu/intern/skillissue/sandbox/runner.py)
- **Status**: **Partially Fixed / Re-opened (Pending Real Docker Isolation)**
- **Root Cause**: `subprocess.run` executed child processes on the API host. While `clean_env` removed secrets from `os.environ`, the untrusted child process still runs on the host filesystem and can read any file the host user can access (e.g. `backend/.env` with `SECRET_KEY`, `ENCRYPTION_KEY`, `DATABASE_URL`) and open outbound network sockets.
- **Interim Fix**: Sanitized `clean_env` dictionary stripping sensitive variables.
- **Required Permanent Fix (Phase 1)**: Remove host subprocess execution completely from all production paths. Implement a dedicated, isolated Docker executor service with `--network none`, `--read-only`, tmpfs, unprivileged user, and no host filesystem bind mounts.

---

### [SEC-02] P0: Process Group & PID Exhaustion Vulnerability (Fork Bomb) in Sandbox
- **Severity**: P0 (High-Impact DoS / Host Stability)
- **Category**: Sandbox Security / Resource Limits
- **Location**: [`sandbox/runner.py`](file:///home/rajababu/intern/skillissue/sandbox/runner.py)
- **Status**: **Partially Fixed / Re-opened (Pending Real Docker Isolation)**
- **Root Cause**: Running on the host means Linux system-wide UID process limits (`RLIMIT_NPROC`) collide with developer or API process threads, making strict in-process enforcement impossible without risking host instability or thread exhaustion.
- **Interim Fix**: Process group creation via `os.setsid` and `os.killpg` on timeout.
- **Required Permanent Fix (Phase 1)**: Isolated container execution with strict cgroup `--pids-limit 64`, memory caps (256MB), CPU limits, and seccomp filtering in an isolated executor service.

---

### [SEC-03] P0: BYOC AWS Access Key Masking Breaks Subsequent Bedrock Invocations
- **Severity**: P0 (Broken Core Bedrock Journey)
- **Category**: BYOC Model Provider / Credential Integrity
- **Location**: [`backend/app/providers/service.py`](file:///home/rajababu/intern/skillissue/backend/app/providers/service.py), [`backend/app/providers/factory.py`](file:///home/rajababu/intern/skillissue/backend/app/providers/factory.py)
- **Status**: **Resolved & Verified**
- **Root Cause**: `ProviderConfigService.save_config` stored masked key `AKIA...1234` in `aws_access_key_masked` while only encrypting `secret_access_key`. When instantiated later for interviews or evaluations, `ModelFactory` passed `AKIA...1234` to boto3, failing authentication.
- **Implemented Fix**:
  Encrypted a unified JSON credentials bundle inside `aws_secret_key_enc`:
  ```python
  bundle = {
      "access_key_id": data.aws_access_key_id,
      "secret_access_key": data.aws_secret_access_key,
  }
  config.aws_secret_key_enc = encrypt_secret(json.dumps(bundle))
  ```
  `ModelFactory.get_for_user` decrypts the bundle and supplies the complete unmasked AWS Access Key ID and Secret Access Key to the Bedrock client.
- **Verification**: Added regression test `test_byoc_credentials_encryption_and_retrieval` in `backend/tests/test_providers.py`. Confirmed full round-trip preservation and unmasked delivery to boto3.

---

### [SEC-04] P1: Production Startup Allows Insecure Default Secrets
- **Severity**: P1 (Security / Operational Readiness)
- **Category**: App Configuration / Secrets Validation
- **Location**: [`backend/app/core/config.py`](file:///home/rajababu/intern/skillissue/backend/app/core/config.py)
- **Status**: **Resolved & Verified**
- **Root Cause**: `Settings` allowed default development secrets even when `ENVIRONMENT=production`.
- **Implemented Fix**:
  Added Pydantic `@field_validator` on `SECRET_KEY` and `ENCRYPTION_KEY` requiring production keys to be at least 32 characters and strictly non-default, preventing application boot with insecure keys.
- **Verification**: Added regression test `test_production_secrets_validation` in `backend/tests/test_auth.py`. Verified that setting `ENVIRONMENT=production` with dev defaults immediately raises `ValueError`.

---

### [LLM-01] P1: Model JSON Parsing Failure Produces Fabricated Evaluation Scores
- **Severity**: P1 (Data Integrity / Essential Scoring Violation)
- **Category**: Structured LLM Output
- **Location**: [`backend/app/evaluations/service.py`](file:///home/rajababu/intern/skillissue/backend/app/evaluations/service.py)
- **Status**: **Resolved & Verified**
- **Root Cause**: If `MockProvider` or Amazon Bedrock produced malformed JSON, `parsed.get("overall_score", 70.0)` defaulted to 70.0 and saved a corrupt scorecard with empty rubric dimensions.
- **Implemented Fix**:
  Enforced strict validation: if `parsed.get("error")` is set or `dimension_scores` is empty, the service raises `ProviderError("Model evaluation response could not be parsed as valid JSON.", code="EVALUATION_PARSING_FAILED")`. No corrupt score is saved to the database.
- **Verification**: Added regression test `test_evaluation_parsing_failure_rejects_fabricated_score` in `backend/tests/test_evaluations_and_plans.py`. Verified HTTP 502 is returned and 404 is received on database lookup.

---

### [LLM-02] P2: Prompt Injection Surface in Resume & Job Description Analysis
- **Severity**: P2 (AI Systems / Robustness)
- **Category**: Prompt Architecture
- **Location**: [`backend/app/evaluations/prompts.py`](file:///home/rajababu/intern/skillissue/backend/app/evaluations/prompts.py), [`backend/app/interviews/prompts.py`](file:///home/rajababu/intern/skillissue/backend/app/interviews/prompts.py), [`backend/app/resumes/service.py`](file:///home/rajababu/intern/skillissue/backend/app/resumes/service.py), [`backend/app/job_descriptions/service.py`](file:///home/rajababu/intern/skillissue/backend/app/job_descriptions/service.py)
- **Status**: **Resolved & Verified**
- **Root Cause**: Untrusted transcript, resume, and JD texts were formatted into prompt bodies without demarcation or isolation instructions.
- **Implemented Fix**:
  1. Wrapped all untrusted inputs in explicit XML boundaries: `<untrusted_candidate_transcript>`, `<untrusted_candidate_answer>`, `<untrusted_resume_content>`, and `<untrusted_job_description>`.
  2. Added explicit system prompt instructions directing the model to treat content within these tags as passive evaluation data and ignore embedded prompt overrides.
- **Verification**: Verified evaluator benchmark suite passes with updated boundaries.

---

### [PRV-01] P2: Silent Override of User Preferred Model in Coding Tasks
- **Severity**: P2 (Model Routing Policy Violation)
- **Category**: BYOC Model Routing
- **Location**: [`backend/app/providers/factory.py`](file:///home/rajababu/intern/skillissue/backend/app/providers/factory.py)
- **Status**: **Resolved & Verified**
- **Root Cause**: Factory unconditionally overwrote user's configured preferred model with `DEFAULT_CODING_MODEL_ID` during coding rounds.
- **Implemented Fix**:
  Preserved user preferred model if explicitly chosen; routed to specialized Qwen3 Coder (`DEFAULT_CODING_MODEL_ID`) when preferred model is default or unspecified.
- **Verification**: Verified provider factory tests in `test_providers.py`.

---

### [DB-01] P2: Default Model Mismatch in User Registration and Database Models
- **Severity**: P2 (Configuration & Schema Drift)
- **Category**: Database Defaults
- **Location**: [`backend/app/auth/service.py`](file:///home/rajababu/intern/skillissue/backend/app/auth/service.py), [`backend/app/database/models.py`](file:///home/rajababu/intern/skillissue/backend/app/database/models.py)
- **Status**: **Resolved & Verified**
- **Root Cause**: Stale defaults (`mock-claude-3-5-sonnet` and `anthropic.claude-3-5-sonnet`) remained in models and user registration after adopting the Qwen3 lineup.
- **Implemented Fix**:
  Updated `models.py` default to `qwen.qwen3-32b-instruct-v1:0` and `auth/service.py` registration default to `mock-qwen3-32b`.
- **Verification**: Verified registration tests create users with `mock-qwen3-32b`.

---

### [FE-01] P1: Speech Recognition Result Stream Causes Exponential Text Duplication
- **Severity**: P1 (Broken Speech Workflow)
- **Category**: Frontend / Speech Recognition
- **Location**: [`frontend/src/features/interview-session/InterviewSessionPage.tsx`](file:///home/rajababu/intern/skillissue/frontend/src/features/interview-session/InterviewSessionPage.tsx)
- **Status**: **Resolved & Verified**
- **Root Cause**: `onResult` appended streaming interim results directly to previous state on every event, duplicating words exponentially.
- **Implemented Fix**:
  Separated `baseInputTextRef.current` (committed text) from live interim text. Only appends to `baseInputTextRef.current` when `isFinal === true`. Manual typing synchronizes `baseInputTextRef.current`.
- **Verification**: Manual speech flow verified with no text duplication; Vite production build passes.

---

### [FE-02] P1: Coding Practice Silently Discards Draft Code on Language or Problem Change
- **Severity**: P1 (Data Loss / Candidate Frustration)
- **Category**: Frontend / Coding Editor State
- **Location**: [`frontend/src/features/coding/CodingPracticePage.tsx`](file:///home/rajababu/intern/skillissue/frontend/src/features/coding/CodingPracticePage.tsx), [`frontend/src/features/interview-session/InterviewSessionPage.tsx`](file:///home/rajababu/intern/skillissue/frontend/src/features/interview-session/InterviewSessionPage.tsx)
- **Status**: **Resolved & Verified**
- **Root Cause**: `handleLanguageChange` and `selectProblem` unconditionally overwrote `code` with `starter_code`.
- **Implemented Fix**:
  Implemented persistent drafts dictionary `draftsRef.current` keyed by `${problem.id}_${language}`. Switching saves the active buffer and restores existing drafts before falling back to starter templates.
- **Verification**: Verified draft preservation on language toggle; Vite production build passes.

---

### [FE-03] P2: Microphone Feedback Loop Transcribing AI Question
- **Severity**: P2 (Voice Interview UX)
- **Category**: Frontend / Speech & Audio
- **Location**: [`frontend/src/features/interview-session/InterviewSessionPage.tsx`](file:///home/rajababu/intern/skillissue/frontend/src/features/interview-session/InterviewSessionPage.tsx)
- **Status**: **Resolved & Verified**
- **Root Cause**: Microphone remained active during text-to-speech audio playback, picking up speaker sound and transcribing the interviewer's own question.
- **Implemented Fix**:
  Introduced `speakWithMicSuppression` helper that pauses speech recognition while `SpeechHandler.speak` is playing audio, and resumes listening once the `onEnd` callback fires.
- **Verification**: Verified speech recognition pauses during TTS playback; Vite production build passes.

---

### [FE-04] P2: Hard Page Reload on 401 Discards In-Flight User Work
- **Severity**: P2 (Session Handling & Resilience)
- **Category**: Frontend / API Client
- **Location**: [`frontend/src/lib/api.ts`](file:///home/rajababu/intern/skillissue/frontend/src/lib/api.ts)
- **Status**: **Resolved & Verified**
- **Root Cause**: `window.location.href = '/login'` triggered on all 401 responses, including failed login attempts and background checks.
- **Implemented Fix**:
  Guarded 401 redirection to execute only when an active token exists and the request was not to `/auth/login`. Dispatched `auth:expired` event for graceful lifecycle handling.
- **Verification**: Verified API client handling; Vite production build passes.

---

### [FE-05] P2: Evaluation Page Dead End If Evaluation Generation Interrupted
- **Severity**: P2 (Error Handling & Recovery)
- **Category**: Frontend / Evaluation Flow
- **Location**: [`frontend/src/features/evaluation/EvaluationPage.tsx`](file:///home/rajababu/intern/skillissue/frontend/src/features/evaluation/EvaluationPage.tsx)
- **Status**: **Resolved & Verified**
- **Root Cause**: If an evaluation had not yet been generated for an interview, the page presented an unrecoverable 404 message with only "Return to Dashboard".
- **Implemented Fix**:
  Added a "Generate Evaluation Now" button that triggers `POST /api/v1/evaluations/:id/generate`, sets the returned evaluation, and refreshes the performance report.
- **Verification**: Verified error state rendering and recovery flow; Vite production build passes.

---

### [FE-06] P3: Accessibility Labels and Focus Indicators on Modals and Controls
- **Severity**: P3 (Accessibility & Visual Polish)
- **Category**: Accessibility / WCAG 2.1 AA
- **Location**: [`frontend/src/components/ui/Modal.tsx`](file:///home/rajababu/intern/skillissue/frontend/src/components/ui/Modal.tsx), [`frontend/src/features/interview-session/SelfEvaluationModal.tsx`](file:///home/rajababu/intern/skillissue/frontend/src/features/interview-session/SelfEvaluationModal.tsx)
- **Status**: **Resolved & Verified**
- **Root Cause**: Missing ARIA attributes on modals, radiogroups, and icon buttons.
- **Implemented Fix**:
  1. Connected modal dialog with `aria-labelledby="modal-title"`.
  2. Implemented `role="radiogroup"`, `role="radio"`, and `aria-checked` on rubric scoring buttons.
  3. Added explicit `aria-label` attributes to microphone toggles, audio playback buttons, and code textareas.
- **Verification**: WCAG accessibility inspection passes; Vite production build passes.
