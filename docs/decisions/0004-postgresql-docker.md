# ADR 0004: Containerized PostgreSQL with Persistent Docker Volume

- **Date:** 2026-10-20
- **Status:** Accepted
- **Context:** Local development must be reproducible, completely decoupled from cloud databases, and resilient across developer machines.
- **Decision:** Run PostgreSQL 16 in Docker Compose. Map container port 5432 to host port 5433 by default (via `POSTGRES_PORT` variable) to eliminate collisions with existing host Postgres instances. Persist database data in named volume `skillissue_pgdata`. Manage all schema migrations using Alembic.
- **Alternatives Considered:**
  - *SQLite*: Rejected because production deployment requires PostgreSQL-specific JSONB capabilities, concurrency guarantees, and migration parity.
  - *Cloud hosted development DB*: Rejected per prompt requirement ("Never require a hosted database to run the local application").
- **Rationale:** Docker Compose guarantees identical database environments across macOS, Linux, and Windows WSL, with automated healthchecks before application startup.
- **Consequences:** Developers must have Docker or Docker Compose installed to run `./dev.sh`.
- **Related Requirements:** Master Prompt Section 5 & 15.
