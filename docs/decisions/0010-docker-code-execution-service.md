# ADR 0010: Isolated Docker Code Execution Service & Threat Model

- **Date:** 2026-10-20
- **Status:** Accepted (Supersedes [ADR 0007](file:///home/rajababu/intern/skillissue/docs/decisions/0007-coding-sandbox-architecture.md))
- **Context:**
  The platform executes untrusted, student-submitted code in Python, Java, and C++. The previous implementation (ADR 0007) relied on in-process host subprocess execution with basic environment variable scrubbing. This left the host filesystem, network interfaces, and database credentials accessible to hostile code (`open("../.env").read()`). Host subprocess execution violates the core security invariants of Skill Issue and must be completely removed from production paths.

- **Decision:**
  1. **Dedicated Executor Microservice (`sandbox/executor/`)**:
     - Extract all Docker container management into a separate, isolated internal executor service.
     - The main application API communicates with the executor over an internal HTTP network using an authenticated shared secret (`X-Executor-Secret`).
     - The main API **never** mounts the Docker socket (`/var/run/docker.sock`). Only the executor has Docker access.
     - The executor has **no network route to PostgreSQL** and holds no application secrets, database credentials, or AWS keys.
  2. **Configurable Runtime**:
     - `SANDBOX_RUNTIME=runc|runsc|kata`. Defaults to `runc` in local development.
     - `runsc` (gVisor) is documented and recommended for production multi-tenant deployments, recognizing that containers alone are not an absolute security boundary.
  3. **Strict Ephemeral Container Policy**:
     - `--network none`: untrusted code has zero network access.
     - `--read-only`: root filesystem is mounted read-only.
     - `--user 10001:10001`: non-root execution inside the container.
     - `--cap-drop ALL` and `--security-opt no-new-privileges`.
     - Seccomp filter (`sandbox/seccomp.json`) blocking `ptrace`, `mount`, `unshare`, `keyctl`, and raw sockets.
     - Memory limits: 256MB RAM / 256MB swap (512MB for Java).
     - CPU limits: 1 CPU core max.
     - Process caps: `--pids-limit 64` to prevent fork bombs.
     - Temporary workspace: 64MB `tmpfs` workdir injected via Docker archive (`put_archive`), with `noexec` on Python and `exec` enabled only for compiled C++/Java binaries.
     - Container labels: `skillissue.sandbox=1`, `skillissue.job=<id>`.
  4. **External Judging & Incremental Output Capping**:
     - Judging occurs outside the container in the executor. Code cannot forge its own evaluation.
     - Stdout and stderr are read incrementally from Docker streaming logs. If output exceeds 1MB (`MAX_OUTPUT_BYTES`), the container is killed immediately and marked `output_limit_exceeded` to prevent memory exhaustion on the host.
     - Exact match, whitespace-insensitive token match, float tolerance, and custom checkers are supported.
  5. **Background Reaper**:
     - On startup and every 60 seconds, a reaper kills and removes all containers carrying `skillissue.sandbox=1` older than 5 minutes.
  6. **Fail-Closed Policy**:
     - Valid `SANDBOX_EXECUTION_MODE` options: `docker` (default), `disabled`, `mock`.
     - In `ENVIRONMENT=production`, if mode is not `docker`, the application refuses to start.
     - Host subprocess execution is deleted from production code. A dev-only escape hatch is restricted behind `ALLOW_UNSAFE_HOST_EXECUTION=1` and strictly disallowed when `ENVIRONMENT=production`.

- **Explicit Threat Model**:
  - **Attacker Goal 1: Read host environment or database credentials.**
    - *Mitigation*: The container has no bind mounts, an empty environment (`env={}`), and no route to Postgres. Code cannot see host filesystem or `.env`.
  - **Attacker Goal 2: Exfiltrate data or reach internal network / AWS metadata.**
    - *Mitigation*: The container is created with `--network none`. No network sockets can be created or connected.
  - **Attacker Goal 3: Host denial of service via fork bomb or memory exhaustion.**
    - *Mitigation*: Hardware cgroups enforce `--pids-limit 64`, `--memory 256m`, and CPU limits. Wall-clock timeouts kill the container via the Docker daemon if cgroups hang.
  - **Attacker Goal 4: Escape container sandbox via kernel exploits.**
    - *Mitigation*: All Linux capabilities dropped (`--cap-drop ALL`), `no-new-privileges` enforced, dangerous syscalls blocked by seccomp (`ptrace`, `unshare`, `mount`, `keyctl`), and support for gVisor (`runsc`) user-space kernel runtime in production.
  - **Attacker Goal 5: Forge judging verdict.**
    - *Mitigation*: Execution results, exit codes, and diffs are computed by the executor supervisor outside the untrusted container. No user-writable result files are trusted.

- **Consequences:**
  - Running code tests locally requires Docker (or `mock` mode for unit tests).
  - Building language images (`scripts/build_sandbox_images.sh`) is required once before running live Docker executions.

- **Related Documents:**
  - PRD Section 9.2, Security Architecture Section 3.
  - Supersedes ADR 0007.
