# ADR 0016: Persistent Sandboxed Executor, User-Controlled Learning Backlog, Bedrock BYOC Onboarding, and Socratic DSA Coaching

## Status
Accepted (Supersedes Sandbox container creation strategy in ADR 0010)

## Date
2026-10-20

## Context
Skill Issue required significant architectural refinements across its core loops to align with production principles:
1. **Sandboxed Code Execution**: The previous execution engine relied on spinning up ephemeral Docker containers per submission, which required mounting the host Docker socket (`/var/run/docker.sock`), incurring heavy container startup latencies (500ms-2000ms), and creating high-severity security vectors.
2. **Provider Onboarding & Registration**: Registration was burdened by career/seniority preferences, and mock provider fallbacks obscured live AWS Bedrock configuration errors. Users required a streamlined account setup followed by an explicit Bedrock BYOC flow with copyable least-privilege IAM policies, real credential verification, and no silent mock degradation in production.
3. **Planly & Learning Backlog Decoupling**: Automatic study plan generation from interview weaknesses violated user agency. Users need a persistent learning backlog where weak topics from interviews can either be queued for later or deliberately imported into user-controlled learning sprints.
4. **DSA Arena Coaching**: DSA practice needed an on-demand, non-automatic AI coaching mentor that provides progressive Socratic hints (nudge -> pattern -> derivation -> pseudocode) without giving away code or triggering unwanted LLM inferences.

---

## Decision

### 1. Persistent Sandbox Executor with Bubblewrap Isolation
- **Persistent Ubuntu Microservice**: Replaced per-run container lifecycle with a persistent executor service (`sandbox/executor/`) running in Docker Compose.
- **Ephemeral Process Supervisor (`bwrap`)**: Each submitted job and compilation step runs under a fully hardened Bubblewrap invocation:
  ```bash
  bwrap --unshare-all --die-with-parent --new-session \
        --ro-bind / / \
        --dev /dev \
        --proc /proc \
        --tmpfs /tmp \
        --bind {job_dir} {job_dir} \
        --chdir {job_dir} \
        --unshare-net \
        --uid 65534 \
        --gid 65534 \
        <language_command>
  ```
  - **Mount namespace**: Read-only root filesystem (`--ro-bind / /`) with private ephemeral `/tmp` (`--tmpfs /tmp`) and job scratch dir (`--bind {job_dir} {job_dir}`).
  - **Process isolation**: Private PID namespace with fresh `/proc` (`--proc /proc`) hiding all external host processes; private virtual devices (`--dev /dev`) containing only standard null/zero/urandom nodes without host disk devices.
  - **Network isolation**: Completely unshared network namespace (`--unshare-net`) with loopback only; sockets to external or local networks fail immediately with `ENETUNREACH`.
  - **Dropped privileges**: Explicitly forced non-root user execution as `nobody:nogroup` (`--uid 65534 --gid 65534`).
  - **Sandboxed Compilation**: C++ (`g++`) and Java (`javac`) compilation steps run inside the exact same Bubblewrap sandbox to prevent `#include` arbitrary file read or compiler exploits.
- **Strict Process Group & Resource Constraints**:
  - Kernel process limit (`RLIMIT_NPROC` / `ulimit -u 64` enforced on UID 65534) halts fork creation inside the sandbox upon reaching limit, preventing thread/process table exhaustion.
  - Full process tree termination via `os.setsid` session groups and `SIGKILL` on timeout.
  - CPU timeout (3.0s wall clock / 2.0s CPU time), memory limits (`RLIMIT_AS` for Python/C++, JVM heap limits for Java), file size limit (10MB), and 1MB maximum stdout/stderr output cap (`output_limit_exceeded`).
  - Compiler sandboxing with resource ceilings (`RLIMIT_CPU`, `RLIMIT_AS`, `RLIMIT_FSIZE`, `ulimit -u`) for C++, Java, and Python syntax checks.
  - Automatic purging of stale job directories on executor startup.
  - Sanitized environment containing only essential runtime variables (`PATH`, `LANG`, `LC_ALL`, `PYTHONUNBUFFERED`, `HOME`, `TMPDIR=/tmp`).
- **Admission Control & Test Result Streaming**:
  - Concurrency admission controller with atomic job slots (`MAX_CONCURRENT_WORKERS`) and HTTP 429 backpressure (`Retry-After: 2`).
  - Incremental test suite progress streamed in real time over Server-Sent Events (SSE) via an asynchronous event queue.
- **Docker Privilege Findings & Production Deployment Boundary**:
  - Running Bubblewrap *inside* a standard Docker container requires `CAP_SYS_ADMIN` and `security_opt: [seccomp=unconfined, apparmor=unconfined]`. Without these, Docker's default AppArmor profile blocks mount propagation (`bwrap: Failed to make / slave: Permission denied`), and Docker's default Seccomp profile blocks `pivot_root` (`bwrap: pivot_root: Operation not permitted`).
  - **Local Development vs. Production Separation**:
    - `compose.yaml` is strictly for local development and developer testing.
    - `compose.prod.yaml` specifies production deployments: the executor MUST run within a dedicated hardware-isolated microVM (e.g. AWS Firecracker, Kata Containers, or Fly.io isolated microVM) or under gVisor `runsc`.
    - **Fail-Closed Guard**: On startup, `sandbox/executor/main.py` checks `ENVIRONMENT` and `SANDBOX_SECURITY_PROFILE`. If `ENVIRONMENT=production` and the profile is not an approved microVM runtime (`hardened_microvm`, `firecracker`, `kata`, `gvisor`, `dedicated_vm`), the service refuses to start.

### 2. Streamlined Registration & Bedrock BYOC Onboarding
- **Essential Registration Only**: User registration (`POST /api/v1/auth/register`) captures only email and password. Seniority, target role, and interview configurations are moved exclusively into interview setup workflows.
- **Dedicated BYOC Onboarding Flow (`/onboarding/bedrock`)**:
  - Redirects newly registered users immediately to Bedrock setup if onboarding is incomplete.
  - Dynamically generates least-privilege IAM policies (`GET /api/v1/providers/iam-policy`) targeting only user-selected models (defaulting to Amazon Nova Lite `amazon.nova-lite-v1:0` and Claude 3.5 Sonnet / Haiku / Llama 3.3).
  - Interactive credential verification (`POST /api/v1/providers/test`) tests AWS credentials against a live Bedrock runtime invocation before marking onboarding complete.
  - Production mock mode is completely eliminated; non-configured environments fail closed with actionable configuration guidance.

### 3. Decoupled Learning Backlog & User-Controlled Planly Sprints
- **Evidence-Based Weakness Extraction**:
  - Completed interviews produce verified `weakness_analysis` records containing topic, subtopic, transcript quote evidence, gap explanation, learning objective, suggested exercise, and confidence ratings.
- **Explicit User Actions**:
  - **Action A ("Add to Planly")**: Directs the user to create or revise an intentional study sprint with custom time commitments and schedules.
  - **Action B ("Queue for Later")**: Adds the topic to `LearningBacklogItem` (`POST /api/v1/learning-backlog/queue-weakness`) with idempotent deduplication across active states (`queued`, `planned`, `in_progress`).
- **Planly Autonomy**:
  - Users can build custom learning plans from scratch without prior interviews or evaluations (`POST /api/v1/plans/custom`).
  - Sprint planners surface queued backlog items as suggestions (`GET /api/v1/plans/{plan_id}/suggested-backlog`), allowing users to explicitly import them (`POST /api/v1/plans/{plan_id}/backlog-items`).
  - No automatic schedules are ever generated without explicit user confirmation.

### 4. Socratic DSA Arena Coaching Agent
- **Explicit On-Demand Action**: Coaching is never triggered by page loads, code changes, or test executions. It is invoked strictly when the user clicks **Need Help?** or submits a mental model question.
- **Progressive Pedagogical Tiers**:
  - **Level 1 (Nudge)**: Invariants, edge-case questions, framing.
  - **Level 2 (Pattern)**: Algorithmic archetype, data structure trade-offs.
  - **Level 3 (Derivation)**: Step-by-step logic, state transition formulas, recurrence relations.
  - **Level 4 (Pseudocode)**: High-level structural pseudocode.
- **Zero Full Solution Leaks**: Prompts strictly prohibit generating complete, runnable code solutions; prompts enforce dry, Gilfoyle-level engineering skepticism and Socratic inquiry.

---

## Consequences & Trade-offs

### Positive
- **Drastic Latency Reduction**: Code execution eliminates the 1-2s Docker container creation overhead; jobs execute in milliseconds under Bubblewrap.
- **Multi-Layered Security**: Eliminates Docker socket sharing on the host; code runs under non-root unshared namespaces with no network, process-count bounds (`ulimit -u 64`), and read-only root filesystems.
- **Production Guardrails**: Insecure container configurations are strictly barred from production via fail-closed startup validation.
- **User Agency Preserved**: Remediation is 100% user-driven. No surprise study plans or unwanted AI charges.
- **Zero AI Mock Slop in Production**: Real Bedrock invocations with least-privilege IAM policies guarantee production parity.

### Trade-offs & Mitigations
- **Container Privilege Trade-offs**: In local Docker Compose, Bubblewrap requires `CAP_SYS_ADMIN` for mount propagation. Mitigated by restricting this exclusively to local development (`compose.yaml`) and requiring dedicated microVMs or VMs in production (`compose.prod.yaml`).
- **Process Resource Limits**: Setting `RLIMIT_NPROC` globally on the parent process disrupts `bwrap` namespace creation. Mitigated by executing user code through an isolated bash wrapper that sets `ulimit -u 64` exclusively on the container's unprivileged UID (65534).
