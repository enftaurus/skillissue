# Baseline Audit Report — Skill Issue (Phase Zero)

**Audit Date & Time**: 2026-10-20T17:28:40+05:30  
**Git Branch**: `main`  
**Git HEAD**: `47d6498` (*feat(agent): implement LangChain + LangGraph agent architecture with provider preferences, memory, and question-level evaluation*)  
**Auditor**: Staff Software Engineer, Backend Architect, AppSec Engineer, Senior Frontend Engineer  

---

## 1. Environment & Runtime Baseline

| Component | Detected Version | Execution Path / Source |
| :--- | :--- | :--- |
| **Operating System** | Linux 6.6.137+ (Ubuntu/Debian x86_64) | Host system |
| **Python** | 3.12.3 | Active in `backend/venv/` |
| **Node.js** | v22.23.3 | Active host Node runtime |
| **npm** | 10.9.9 | Active host npm runtime |
| **PostgreSQL** | PostgreSQL 16.8 (Alpine) | Container `skillissue-postgres` (ports `127.0.0.1:5433->5432`) |
| **Docker Compose** | Docker Compose v2.30.3 | Defined in `compose.yaml` |
| **Local Entrypoint** | `./dev.sh` (bash) | Supports `--check`, `--stop`, `--reset-db` |

---

## 2. Dependency Inconsistency Inspection

Inspection of the declared dependency sources across the repository:

1. **`backend/pyproject.toml`** (Primary declared dependencies):
   - Declares: `fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `asyncpg`, `psycopg2-binary`, `alembic`, `boto3`, `cryptography`, `bcrypt`, `python-jose`, `docker`, `pypdf`, `langchain-core`, `langgraph`, `langgraph-checkpoint`, `langgraph-checkpoint-postgres`, `langchain-aws`, `pytest`, `pytest-asyncio`.
2. **`backend/requirements.txt`** (Secondary legacy requirements file):
   - **Critical Gap Detected**: Missing `langchain-core`, `langgraph`, `langgraph-checkpoint`, `langgraph-checkpoint-postgres`, `langchain-aws`, and `docker`.
   - **Impact**: Any environment initialized via `dev.sh` (`pip install -r backend/requirements.txt`) fails immediately with `ModuleNotFoundError: No module named 'langchain_core'` on application boot.
3. **`backend/Dockerfile`**:
   - **Critical Gap Detected**: Line 13 executes hardcoded `RUN pip install ...` without `langchain-core`, `langgraph`, `langgraph-checkpoint`, `langgraph-checkpoint-postgres`, `langchain-aws`, and `docker`.
   - **Impact**: Container builds fail on startup when running `uvicorn backend.app.main:app`.
4. **`frontend/package.json` & `frontend/package-lock.json`**:
   - Synchronized with Vite 5.1.6, React 18.2.0, Monaco Editor 4.7.0, Tailwind CSS 3.4.1, Recharts 3.10.1.

---

## 3. Pre-Modification Baseline Command Results

| Verification Check | Exact Command | Exit Code | Observed Output / Status |
| :--- | :--- | :---: | :--- |
| **Git Working Tree** | `git status` | `0` | Clean working tree on `main` (commit `47d6498`). |
| **System Prerequisites** | `./dev.sh --check` | `0` | Python 3.12, Node 22, npm, Docker, Postgres on 5433 verified. |
| **Alembic Migration State** | `backend/venv/bin/alembic -c backend/alembic.ini current` | `0` | `0004_provider_prefs_memory (head)` applied cleanly. |
| **Backend Unit & Integration Tests** | `PYTHONPATH=. backend/venv/bin/pytest backend/tests -v` | `0` | **15 passed** in 9.84s (100% pass rate). |
| **Evaluator Quality Benchmarks** | `PYTHONPATH=. backend/venv/bin/python3 scripts/run_benchmarks.py` | `0` | **20/20 benchmark cases** passed calibration bounds. |
| **Adversarial Sandbox Security** | `PYTHONPATH=. backend/venv/bin/python3 scripts/sandbox_escape_suite.py` | `0` | **8/8 security tests passed** (UID 10001, net isolation, cgroups). |
| **Frontend Production Build** | `npm --prefix frontend run build` | `0` | TypeScript check passed, Vite bundled in 2.61s. |

---

## 4. Priority Issues Identified for Remediation

1. **Dependency Split & Docker Build**: Reconcile `backend/requirements.txt` and `backend/Dockerfile` with `backend/pyproject.toml`.
2. **Turn Lifecycle & Idempotency**: Add turn IDs, client submission tokens, and idempotency protection on `/interviews/{id}/message`. Prevent state corruption on concurrent submissions.
3. **Persistent Checkpointer Resilience**: Require durable PostgreSQL checkpointer in production; fail closed with actionable operational error instead of silent module-global `_memory_saver` fallback.
4. **Keyword Fallback Removal & Explicit Topic Status**: Replace brittle string matching (`redis`, `faster`, `saga`) with deterministic rubric-based assessment; track explicit topic lifecycle (`not_started`, `in_progress`, `assessed`, `needs_follow_up`).
5. **Interview Memory Growth**: Fix rolling summary logic (currently frozen after first generation) to continuously incorporate candidate claims, strengths, and open follow-up threads.
6. **Unified Provider & Client Resolution**: Unify LangChain chat models and legacy provider calls under a cohesive, task-aware resolver with explicit fallback logging and client cache invalidation.
7. **Evidence Grounding & Idempotent Evaluation**: Validate quote fidelity strictly against exact candidate answers for that specific turn; ensure repeated evaluation requests do not corrupt or duplicate EMA user skills.
8. **Frontend Resilience**: Eliminate optimistic message loss on network errors, preserve draft text on failure, support self-evaluation persistence, and replace modal blocking alerts in coding practice with accessible inline alerts.
