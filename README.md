# Skill Issue

> *Your interview went badly. Good. Now we have data.*

Skill Issue is an AI-powered interview preparation and career-readiness platform that helps students discover their weaknesses, improve through personalized practice, and measure verifiable progress.

---

## The Core Loop

```
Practice → Self-evaluate → Receive evidence-based feedback → Improve (Planly) → Reassess → Measure progress
```

- **Domain-based & JD-based modes**: Practice against customized skill sets or extract requirements directly from actual Job Descriptions.
- **Realistic Human Interviewing**: Direct, adaptive questioning that probes technical depth, challenges vague claims, and avoids AI sycophancy.
- **BYOC (Bring Your Own Cloud)**: Connect your own Amazon Bedrock credentials with zero markup, token usage tracking, and cost estimation.
- **Planly Adaptive Improvement Engine**: Dynamic multi-day improvement plans with concrete tasks and curated learning resources.
- **Secure Code Execution Sandbox**: Multi-language execution (Python, Java, C++) in isolated environments.

---

## Quick Start (One Command)

The entire local development environment starts with a single command:

```bash
chmod +x dev.sh
./dev.sh
```

This will:
1. Validate environment configuration (generating `.env` if missing).
2. Spin up PostgreSQL 16 via Docker Compose on port `5433` (persisting to Docker volume `skillissue_pgdata`).
3. Apply database migrations via Alembic.
4. Launch the FastAPI backend at [http://localhost:8000](http://localhost:8000).
5. Launch the React + Vite frontend at [http://localhost:5173](http://localhost:5173).

### Useful CLI Flags

```bash
./dev.sh --check     # Inspect dependencies, configurations, and health
./dev.sh --stop      # Cleanly stop all development servers and containers
./dev.sh --reset-db  # Reset local development database (destroys volume, re-migrates)
```

---

## Architecture at a Glance

```
React (TypeScript + Vite + Tailwind) [Port 5173]
                  │
                  ▼
         FastAPI Modular Monolith [Port 8000]
         ├── Auth (JWT + Tenant Isolation)
         ├── BYOC Provider Factory (Bedrock + Mock Engine)
         ├── Interview Engine (Domain & JD Modes)
         ├── Evaluation & Rubric Service
         ├── Planly Adaptive Learning Engine
         └── Sandbox API (Python, Java, C++)
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
PostgreSQL 16           Coding Sandbox
[Port 5433]             (Isolated runner)
```

For detailed architecture diagrams and security boundaries, see [`docs/architecture/overview.md`](file:///home/rajababu/intern/skillissue/docs/architecture/overview.md).

---

## Documentation Index

- [Architecture Overview](file:///home/rajababu/intern/skillissue/docs/architecture/overview.md)
- [Security Architecture](file:///home/rajababu/intern/skillissue/docs/architecture/security.md)
- [Architecture Decision Records (ADRs)](file:///home/rajababu/intern/skillissue/docs/decisions/README.md)
- [Codebase Knowledge Graph](file:///home/rajababu/intern/skillissue/docs/knowledge-graph/README.md)
- [AWS Bedrock Setup Guide](file:///home/rajababu/intern/skillissue/docs/product/aws-bedrock-setup.md)
- [Local Development Guide](file:///home/rajababu/intern/skillissue/docs/operations/local-development.md)
- [Environment Variables](file:///home/rajababu/intern/skillissue/docs/operations/environment-variables.md)

---

## License & Usage

Skill Issue is engineered for students and learners. Evaluator scores are coaching estimates, not guarantees of employment or hiring decisions.
