# Baseline Audit Report — Skill Issue

**Date & Time**: 2026-10-20T03:28:40+05:30  
**Git Branch**: `main`  
**Git HEAD**: `d54a42b` (*feat(frontend): complete React UI, Cockpit Dashboard, Planly Roadmap, Progress Analytics, Coding Sandbox, and Speech integration*)  
**Auditor**: Staff Full-Stack Engineer, AppSec Engineer, Senior Frontend Engineer  

---

## 1. Environment & Runtime Baseline

| Component | Detected Version | Status / Notes |
| :--- | :--- | :--- |
| **Operating System** | Linux (Ubuntu/Debian x86_64) | Normal |
| **Python** | 3.12.3 | In `backend/venv/` with all pinned dependencies installed |
| **Node.js** | v22.23.3 | Active |
| **npm** | 10.9.9 | In `frontend/node_modules/` |
| **PostgreSQL** | 16-alpine (Docker container `skillissue-postgres`) | Port mapped to `5433:5432` to avoid host collisions; healthy |
| **Docker Compose** | Compose v2 (`compose.yaml`) | Named volume `skillissue_pgdata` intact |
| **Single Dev Entrypoint** | `./dev.sh` (supports `--check`, `--stop`, `--reset-db`) | Fully functional |

---

## 2. Pre-Audit Verification Checks

### 2.1 Working Tree Integrity
- `git status`: Branch `main` is up to date with `origin/main`.
- Untracked files: `digest.txt` (preserved, not touched).
- Zero uncommitted code modifications.

### 2.2 Local Dev System Check (`./dev.sh --check`)
- **Command**: `./dev.sh --check`
- **Exit Code**: `0`
- **Output Summary**:
  - Host requirements verified
  - Docker container `skillissue-postgres` is Up and healthy
  - PostgreSQL reachable on port 5433
  - Backend venv present, `uvicorn` and dependencies installed
  - Frontend `node_modules` present

### 2.3 Database Migration Check
- **Command**: `alembic -c backend/alembic.ini current`
- **Exit Code**: `0`
- **Current Head**: `0001_initial_schema (head)`
- **Schema Drift**: No pending unapplied migrations; initial schema fully matches PostgreSQL database.

### 2.4 Application Startup
- **Command**: `python3 -c "import backend.app.main as m; print('FastAPI app loaded successfully:', m.app.title)"`
- **Exit Code**: `0`
- **Result**: `FastAPI app loaded successfully: Skill Issue`

### 2.5 Backend Test Suite
- **Command**: `PYTHONPATH=. pytest backend/tests -v`
- **Exit Code**: `0`
- **Execution Time**: 4.94s
- **Results**: 9 passed, 0 failed, 0 skipped
  - `backend/tests/test_auth.py` (Registration, login, JWT token issuance, profile update, cascade delete)
  - `backend/tests/test_benchmarks.py` (JSON output parsing & schema bounds)
  - `backend/tests/test_coding.py` (Sandboxed code execution in Python, Java, C++, timeout, memory limits)
  - `backend/tests/test_evaluations_and_plans.py` (Post-interview evaluation, Planly roadmap generation, schedule adaptation)
  - `backend/tests/test_interviews.py` (Domain & JD mode interviews, adaptive questioning, message history)
  - `backend/tests/test_providers.py` (Bedrock factory, MockProvider fallback, encryption/decryption at rest)
  - `backend/tests/test_quality_tone.py` (Persona verification, anti-sycophancy, concise questioning)

### 2.6 Frontend Compilation & Typecheck
- **Command**: `npm run build` in `frontend/`
- **Exit Code**: `0`
- **Execution Time**: 1.35s
- **Output Bundle**:
  - `dist/index.html`: 1.04 kB
  - `dist/assets/index-zQRSTg_z.css`: 33.11 kB
  - `dist/assets/index-BY6GneR1.js`: 296.07 kB
- **TypeScript**: 0 errors, strict flags enabled (`noUnusedLocals`, `noUnusedParameters`).

### 2.7 Evaluator Benchmark Suite
- **Command**: `PYTHONPATH=. python3 scripts/run_benchmarks.py`
- **Exit Code**: `0`
- **Results**: 4/4 benchmark scenarios calibrated successfully:
  - `tech_strong_redis`: Schema VALID, Score: 78.5/100, 3 strengths, 3 weaknesses
  - `tech_false_confident`: Schema VALID, Score: 78.5/100, 3 strengths, 3 weaknesses
  - `behavioral_star_strong`: Schema VALID, Score: 78.5/100, 3 strengths, 3 weaknesses
  - `dsa_complexity_error`: Schema VALID, Score: 78.5/100, 3 strengths, 3 weaknesses

---

## 3. Scope for Deep Staff Audit

With the baseline firmly established, the audit will proceed into:
1. **Backend & API Deep Dive**: Authorization & cross-tenant security invariants, credential rotation, rate limiting, async blocking I/O, error handling.
2. **AWS Bedrock & Model Provider Verification**: Credential encryption, region availability, cost calculation, fallback failure modes.
3. **Structured LLM Output & Prompt Injection**: Schema parsing resilience, prompt delimiters, ungrounded score prevention.
4. **Coding Sandbox Security Boundary**: Subprocess sandboxing, PID exhaustion / fork bombs, filesystem isolation, network egress blocking.
5. **Frontend Comprehensive Audit**: Page-by-page review, speech recognition lifecycle & error recovery, form drafts preservation, responsiveness, accessibility tokens.
