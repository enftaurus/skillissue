# ADR 0007: Isolated Coding Sandbox Architecture

- **Date:** 2026-10-20
- **Status:** Superseded by [ADR 0010: Isolated Docker Code Execution Service](file:///home/rajababu/intern/skillissue/docs/decisions/0010-docker-code-execution-service.md)
- **Context:** Candidate coding rounds in Python, Java, and C++ require running untrusted user-submitted code without endangering server infrastructure, hosting credentials, or adjacent user data.
- **Decision:** Implement a private sandbox execution boundary with multi-layer isolation:
  1. Primary container mode: Ephemeral Docker container execution with `--net none`, memory caps (256MB), CPU time limit (5s), unprivileged UID (10001), and read-only rootfs.
  2. Fallback isolated process mode: Unprivileged sandboxed execution with `ulimit` and timeout constraints for environments where Docker-in-Docker is restricted.
- **Alternatives Considered:**
  - *Judge0 API integration*: Considered as a future cloud alternative, but rejected for initial implementation to keep local development zero-dependency and self-contained.
  - *In-process Python `exec()`*: Rejected as a critical remote code execution vulnerability.
- **Rationale:** Strict container isolation prevents untrusted code from accessing environment secrets, host ports, or database sockets.
- **Consequences:** Local development requires Docker or standard host compilers (`python3`, `g++`, `javac`) to run code tests.
- **Related Requirements:** PRD FR-13, Section 9.2; Master Prompt Section 11.
