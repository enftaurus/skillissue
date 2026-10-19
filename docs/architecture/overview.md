# Architecture Overview — Skill Issue

## 1. System Philosophy

Skill Issue is built as a **modular monolith** with an explicit boundary for untrusted code execution. This design strikes the optimal balance between high velocity, code maintainability, clear module encapsulation, and bulletproof security for untrusted code execution.

---

## 2. Component Topology

```
┌─────────────────────────────────────────────────────────────┐
│                 React SPA (Vite + Tailwind)                │
│    Light theme, accessible design tokens, Web Speech API   │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Modular Application                 │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Auth & Users │  │ Model Factory│  │ Interview Engine │  │
│  │ (JWT, RBAC)  │  │ (Bedrock/Mock│  │ (Domain & JD)    │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                   │             │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌────────┴─────────┐  │
│  │ Evaluation   │  │ Planly Engine│  │ Coding Sandbox   │  │
│  │ & Rubrics    │  │ (Adaptive)   │  │ Coordinator      │  │
│  └──────────────┘  └──────────────┘  └────────┬─────────┘  │
└──────────────┬────────────────────────────────┼─────────────┘
               │                                │
               ▼                                ▼
     ┌──────────────────┐             ┌───────────────────┐
     │  PostgreSQL 16   │             │ Isolated Sandbox  │
     │  (Docker volume) │             │ (Python/Java/C++) │
     └──────────────────┘             └───────────────────┘
```

---

## 3. Core Modules

### 3.1 Authentication & Profile (`backend/app/auth`)
- Manages user lifecycle, registration, login via JWT bearer tokens.
- Enforces strict tenant isolation: every resource lookup filters by `user_id`.
- Account deletion removes all stored evaluations, transcripts, plans, and provider credentials.

### 3.2 BYOC Model Factory (`backend/app/providers`)
- Encapsulates LLM provider access. Supported production provider: **Amazon Bedrock**.
- Built-in `MockProvider` enables seamless offline local development and automated testing without AWS costs.
- Stores user credentials encrypted at rest with AES-GCM (`cryptography.fernet`).
- Models Catalog maintains verified models, regional availability, token limits, and input/output pricing.
- Tracks estimated token usage and session cost against the $20 student planning budget.

### 3.3 Interview Engine (`backend/app/interviews`)
- Single unified engine serving both **Domain-based** (user selected / resume skills) and **Job-Description-based** (extracted requirements) modes.
- Four interview categories: Technical, HR/Behavioural, DSA (with coding), Managerial/Role-specific.
- Conversational controller enforcing:
  - Exactly 1 question at a time.
  - Realistic human tone (direct, skeptical, inquisitive).
  - Adaptive follow-ups and clarification triggers.
  - Text fallback for browser voice input.

### 3.4 Evaluation & Rubrics (`backend/app/evaluations`)
- Separate post-interview evaluation pass.
- Versioned rubrics per category.
- Compares student's self-evaluation against AI evaluation.
- Returns evidence-linked findings: exact transcript quotes, identified gaps, concrete corrective steps, and uncertainty indicators.

### 3.5 Planly (`backend/app/plans`)
- Personalized improvement engine.
- Generates multi-day task calendars prioritizing identified weaknesses.
- Dynamically adapts schedule if user misses days or demonstrates mastery in reassessments.

### 3.6 Coding Sandbox (`backend/app/coding` & `sandbox/`)
- Isolates untrusted student code execution (Python 3, Java 21, C++17).
- Applies non-root execution, CPU limits (5s), memory limits (256MB), process limits, and network disabling.
- Returns standardized test outcomes (stdout, stderr, exit code, execution time, pass/fail per testcase).
