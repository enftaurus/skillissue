# 0023. Project Test Sandbox Hardening & Server-Side Copilot Prompt Log

- **Status**: Accepted
- **Date**: 2026-11-05
- **Deciders**: QA / Platform Engineering
- **Consulted**: Security

---

## Context

The 2026-11-05 QA audit (`docs/reports/qa-audit-2026-11-05.md`) found that AI-Assisted Coding Projects:

1. Ran candidate code via `subprocess` on the API host. With bubblewrap, `/` was bind-mounted read-only and the API process environment was inherited, so candidate code could read the repository `.env` (including `SKILLISSUE_SECRET_KEY` and DB credentials) and return it in an assertion message. Without bubblewrap (e.g. the production Docker image, which does not ship it), pytest ran directly in the API container with all production secrets.
2. Took pass/fail from pytest stdout. Code that implemented nothing printed fake `PASSED` lines to pytest's saved stdout fd, then called `os._exit(0)`, and was reported as `passed 17/17`.
3. Let clients overwrite any non-test repository file, not just the editable ones.
4. Computed the prompt-engineering score from `conversation_history` sent by the client, so a candidate could submit any history and get 100/100.
5. Called a non-existent `provider.generate()`, so the "AI pair programmer" silently served canned heuristics and never reached the LLM.

This violates Security Invariant #2 (untrusted code must never run directly on the host API process) and makes project scores meaningless.

## Decision

1. **Hardened runner** (`backend/app/projects/sandbox.py`):
   - Bubblewrap with **no host root mount**: only `/usr`, system libraries and the interpreter's virtualenv are bound read-only. Cleared env (`--clearenv`), no network, uid 65534, `--die-with-parent`, a private `/tmp`, and a `/work` job dir.
   - Only `editable_files` may be overlaid. Tests and infrastructure always come from the server.
   - Results come from a **JUnit XML report** at a random path. They are cross-checked against test names parsed (AST) from the authoritative test files and against the pytest exit code. Any mismatch → `error` with `integrity_flags`.
   - A **static integrity scan** of candidate files (code tokens only, not comments) rejects harness-tampering primitives (`os._exit`, raw fd writes, `sys.modules`, `_pytest`, `ctypes`, `subprocess`, `open`, `eval`, environment access, host paths) before execution.
   - **Fail closed** with `503 SANDBOX_UNAVAILABLE` when bubblewrap is missing. A developer can opt in with `ALLOW_UNSANDBOXED_PROJECT_TESTS=true`, which is never honoured in production.
   - Runs execute in a worker thread, so the event loop is not blocked.
2. **Server-side prompt log**: new table `project_copilot_turns` (migration `0015`). Every copilot turn is persisted. `evaluate-prompts` and `submit` score only the turns logged since the user's previous submission of that project. Client-supplied history is ignored.
3. The copilot calls `generate_text()` and wraps workspace files and questions in untrusted-data delimiters.

## Alternatives Considered

- **HMAC-signed prompt receipts (stateless)**: rejected, because a candidate could still omit embarrassing prompts.
- **Run projects in the Docker executor now**: preferred long-term. The executor currently only judges single-file stdin/stdout programs, so a project mode with an out-of-process assertion harness is follow-up work.

## Consequences & Trade-offs

- **Residual risk**: candidate code still runs in the same process as pytest. A determined attacker who evades the static scan could forge the JUnit file. The durable fix is an out-of-process harness in the Docker executor (follow-up).
- The static scan may reject unusual but legitimate code (e.g. `getattr`). The reason is shown to the candidate with file and line.
- Production deployments without bubblewrap now refuse project test runs instead of silently executing on the host. The backend image needs bubblewrap (with user namespaces), or project runs must move to the executor.

## Related Requirements

- AGENTS.md Security Invariants #1 (Zero Secret Leaks) and #2 (Untrusted Code Execution)
- PRD: AI-assisted work simulations, prompt-quality feedback
