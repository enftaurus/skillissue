# AGENTS.md — Agent Onboarding and Engineering Guide

Welcome to **Skill Issue**. Before modifying any code, reading or modifying architecture, or adding features, you must read and adhere to this document.

## 1. Product Purpose & Brand Identity

Skill Issue is an AI-powered career-readiness and interview preparation platform that helps engineering students discover weaknesses, improve through personalized practice, and measure their progress.

### The Core Loop
```
Practice → Self-evaluate → Receive evidence-based feedback → Improve (Planly) → Reassess → Measure progress
```

### Brand Tone & Persona
- **Tagline**: *"Your interview went badly. Good. Now we have data."*
- **Persona**: Gen Z wit meets Gilfoyle-level engineering precision.
- **Voice**: Direct, dry, intelligent, occasionally sarcastic, respectful of the learner.
- **Never**: Condescending, sycophantic ("Great job! That's a wonderful explanation!"), artificially enthusiastic, or generic AI slop.

### Visual Direction
- **Strictly Light Theme**: Warm white (`#FAFAFA`, `#F4F4F5`, `#FFFFFF`), dark text (`#09090B`, `#18181B`), restrained acid-lime/green accents (`#84CC16`, `#65A30D`), subtle borders (`#E4E4E7`), understated shadows.
- Avoid fake neon hacker/terminal aesthetics across consumer views, avoid dense enterprise clutter.

---

## 2. Location of Source Documents & Specifications

- Product Requirements: [`prd.md`](file:///home/rajababu/intern/skillissue/prd.md)
- Architecture Overview: [`docs/architecture/overview.md`](file:///home/rajababu/intern/skillissue/docs/architecture/overview.md)
- Security Architecture: [`docs/architecture/security.md`](file:///home/rajababu/intern/skillissue/docs/architecture/security.md)
- Architecture Decisions: [`docs/decisions/README.md`](file:///home/rajababu/intern/skillissue/docs/decisions/README.md)
- Knowledge Graph: [`docs/knowledge-graph/README.md`](file:///home/rajababu/intern/skillissue/docs/knowledge-graph/README.md)
- AWS Bedrock Setup Guide: [`docs/product/aws-bedrock-setup.md`](file:///home/rajababu/intern/skillissue/docs/product/aws-bedrock-setup.md)
- Local Development: [`docs/operations/local-development.md`](file:///home/rajababu/intern/skillissue/docs/operations/local-development.md)

### Source-of-Truth Hierarchy
1. Explicit decisions recorded by the product owner.
2. Confirmed requirements in `prd.md`.
3. Accepted Architecture Decision Records (`docs/decisions/`).
4. Existing code and automated test assertions.
5. Engineering judgment for unresolved implementation details.

---

## 3. Technology Stack & Key Decisions

- **Frontend**: React 18+, TypeScript, Vite, Tailwind CSS, Lucide React icons, React Router v6.
- **Backend**: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async/sync engine), Alembic.
- **Database**: PostgreSQL 16 in Docker Compose (named volume `skillissue_pgdata`, mapped to host port 5433 by default to prevent collisions).
- **Inference & BYOC**: Amazon Bedrock via application-owned Model Factory. Features mock provider for zero-cost, offline local development. No LiteLLM. No LangGraph in initial architecture.
- **Coding Sandbox**: Isolated ephemeral container/process execution with non-root user, memory limits, CPU timeouts, and disabled network access.
- **Secrets Management**: Credentials encrypted at rest using AES-GCM / Fernet (`SKILLISSUE_SECRET_KEY`). Never logged, masked in UI, isolated per tenant.

---

## 4. Development & Operation Commands

The single entry point for local development is `./dev.sh`:

```bash
chmod +x dev.sh
./dev.sh              # Start PostgreSQL, apply migrations, start backend & frontend
./dev.sh --check      # Verify dependencies, configs, and service connectivity
./dev.sh --stop       # Safely shut down all background services & containers
./dev.sh --reset-db   # Destroy local test DB and re-migrate (requires confirmation)
```

### Testing Commands
```bash
# Backend unit & integration tests
pytest backend/tests -v

# Run evaluator benchmarks
python3 scripts/run_benchmarks.py

# Regenerate Codebase Knowledge Graph
python3 scripts/generate_knowledge_graph.py
```

---

## 5. Decision Log Workflow (ADRs)

Any non-trivial architectural, framework, security, or data model change MUST be accompanied by an Architecture Decision Record in `docs/decisions/`:
- Filename format: `docs/decisions/NNNN-short-descriptive-slug.md`
- Status lifecycle: `proposed` → `accepted` → `superseded` / `rejected`
- Maintain the index in `docs/decisions/README.md`.
- Never rewrite history. When modifying a past decision, mark the old record `superseded by NNNN` and create the new record.

---

## 6. Codebase Knowledge Graph Maintenance

The repository contains a machine-readable knowledge graph:
- Authoritative JSON: `docs/knowledge-graph/graph.json` (Schema v1.0)
- Visual Mermaid diagram: `docs/knowledge-graph/graph.mmd`
- Feature map: `docs/knowledge-graph/feature-map.md`
- Dependency map: `docs/knowledge-graph/dependency-map.md`

Whenever you add or remove routes, models, services, or ADRs, run:
```bash
python3 scripts/generate_knowledge_graph.py
```

---

## 7. Model Providers & Interview Behavior Guidelines

### Adding / Modifying a Model Provider
1. Inherit from `BaseProvider` in `backend/app/providers/base.py`.
2. Register the provider in `backend/app/providers/factory.py`.
3. Add verified models, context limits, and pricing metadata to `backend/app/providers/models_catalog.py`.
4. Never dynamically import arbitrary classes or instantiate providers from unsanitized database strings.
5. All credentials must be decrypted in memory only when executing a validated request, never stored in plaintext or logged.

### Realistic Human Interview Style
Interview prompts in `backend/app/interviews/prompts.py` must enforce:
1. **One question at a time**.
2. **Short, direct sentences** like an experienced senior engineer or hiring manager.
3. **No generic praise**: Do not say "Great answer!", "That is fascinating!", or "Let's dive deep into your profound journey."
4. **Adaptive follow-ups**: If the candidate makes an unverified claim ("Redis made it 10x faster"), follow up with: *"How did you measure that 10x improvement?"*
5. **Polite skepticism**: If an answer is vague, ask for concrete implementation details or trade-offs.

---

## 8. Security Invariants

1. **Zero Secret Leaks**: IAM access keys and session tokens must never appear in logs, error messages, URLs, browser storage, or client-side bundles.
2. **Untrusted Code Execution**: Candidate code must NEVER be executed directly on the host API process. It must run through the sandboxed runner with strict resource limits and no network.
3. **User Isolation**: Every database query accessing candidate interviews, profiles, resumes, or evaluations must filter by the authenticated `user_id`.
4. **Offline Dev Mode**: The app must fully boot and function using the built-in `MockProvider` without requiring real AWS credentials or internet access.
