# 0026. Sandbox without procfs, non-root executor

- **Status**: Accepted
- **Date**: 2026-11-06

## Context
Under Docker compose every sandboxed run failed with `bwrap: Can't mount proc on /newroot/proc: Operation not
permitted`. Container runtimes mask parts of `/proc` (`/proc/kcore`, `/proc/sys`, ...), and the kernel refuses a fresh
procfs mount in a child namespace when the parent's view is partially hidden. The only Docker-side fix is
`systempaths=unconfined`, which unmasks the host's `/proc` paths for the whole container. We rejected that.

While fixing it we found a second defect: the executor ran as root, so bubblewrap's user namespace mapped the job to
kernel uid 0. The kernel exempts the root user from `RLIMIT_NPROC`, so `ulimit -u 64` did nothing and a 500-process
fork bomb completed.

## Decision
1. Both runners (DSA executor and project test runner) mount an **empty tmpfs at `/proc`** instead of procfs. Candidate
   code sees no `/proc/<pid>/environ`, `maps`, `mounts`, or cgroup data. That is strictly less exposure than before.
2. The JDK resolves its own libraries through `$ORIGIN`, which needs `/proc/self/exe`. The executor resolves real
   `java`/`javac` paths and sets `LD_LIBRARY_PATH`/`JAVA_HOME` explicitly.
3. The bubblewrap invocation uses `--clearenv` and rebuilds a minimal environment, so executor variables
   (`EXECUTOR_SECRET`) can never reach compile or run steps.
4. The executor image runs as **uid 10001**. `cap_add: SYS_ADMIN` is removed and `pids_limit: 512` is a container-level
   backstop.
5. `seccomp=unconfined` and `apparmor=unconfined` remain in the dev compose profile. Docker's default profiles block
   user-namespace creation and private mounts. Production keeps the gVisor/Kata plan in `compose.prod.yaml`.

## Consequences
- DSA runs (Python, C++, Java) and AI-project test runs work under compose. Verified in-container: env leak, `/proc`
  listing, network and fork bomb are all contained.
- Code that legitimately reads `/proc` (for example `/proc/self/status` for memory) gets nothing. No curated problem
  or project does this.
