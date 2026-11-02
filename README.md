# Skill Issue

<p align="center">
  <img src="https://raw.githubusercontent.com/enftaurus/skillissue/main/docs/assets/banner.png" alt="Skill Issue Banner" width="100%" onerror="this.style.display='none'"/>
</p>

<p align="center">
  <strong>AI-Powered Career-Readiness & Technical Interview Preparation Platform</strong><br>
  <em>“Your interview went badly. Good. Now we have data.”</em>
</p>

<p align="center">
  <a href="#key-features"><img src="https://img.shields.io/badge/Platform-Full--Stack-indigo.svg" alt="Platform"/></a>
  <a href="#technology-stack"><img src="https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.12-blue.svg" alt="Backend"/></a>
  <a href="#technology-stack"><img src="https://img.shields.io/badge/Frontend-React%2018%20%7C%20TypeScript%20%7C%20Vite-emerald.svg" alt="Frontend"/></a>
  <a href="#dual-cloud-byoc"><img src="https://img.shields.io/badge/Inference-AWS%20Bedrock%20%2B%20Azure%20OpenAI-orange.svg" alt="Cloud BYOC"/></a>
  <a href="#cross-browser-cloud-neural-audio"><img src="https://img.shields.io/badge/Speech-Cloud%20Neural%20TTS%20%2B%20Whisper-purple.svg" alt="Audio Pipeline"/></a>
  <a href="#quick-start-one-command"><img src="https://img.shields.io/badge/Setup-One--Command%20Dev-lime.svg" alt="Dev"/></a>
</p>

---

## The Core Loop

Skill Issue is built for engineering students and developers who want realistic, rigorous interview preparation without AI sycophancy or generic flattery.

```
Practice → Self-evaluate → Receive evidence-based feedback → Improve (Planly) → Reassess → Measure progress
```

- **Zero Generic AI Praise**: No *"Great explanation!"* or *"Fascinating journey!"*. The interviewer persona embodies senior engineering rigor—direct, skeptical, inquisitive, and polite.
- **Adaptive Questioning**: Automatically probes unverified claims (*"You said Redis made it 10x faster. How exactly did you measure that?"*) and adjusts difficulty dynamically.
- **Evidence-Based Evaluations**: Every score is backed by verbatim candidate quotes, rubric citations, and concrete counter-examples of what could have been articulated better.

---

## Key Features

### 1. Realistic Technical & Behavioral Interviews
- **Domain-Based Practice**: Choose custom technical competency stacks (PostgreSQL, Distributed Systems, Redis, System Design, FastAPI, Docker, Kafka, Microservices, Linux Internals).
- **JD-Based Practice**: Paste real Job Descriptions; the platform extracts target roles, technical requirements, and company context for targeted preparation.
- **Resume-Grounded Probing**: Upload PDF or text resumes. The interviewer analyzes your listed projects and probes your actual technical claims.
- **Interview Tracks**: Dedicated preparation modes for **Technical System Architecture**, **Behavioral (STAR method)**, **Data Structures & Algorithms**, and **Engineering Management**.
- **Adaptive Difficulty**: Automatic tier adjustments between Junior, Intermediate, and Advanced based on candidate performance.

### 2. Cross-Browser Cloud Neural Audio (TTS & STT)
- **Universal Browser Parity**: Flawless studio-quality audio in **Firefox, Chrome, Safari, and Edge**.
- **Solves Firefox Audio Quality**: Bypasses the local operating system synthesizers (`espeak-ng`) in Firefox by streaming high-clarity 48kHz neural MP3 audio over HTML5.
- **Cross-Browser Speech-to-Text**: Replaces Chromium-only `webkitSpeechRecognition` with W3C `MediaRecorder` audio capture, enabling voice answers in any browser.
- **4-Tier Speech Architecture**:
  1. **Azure OpenAI Audio** (`tts-1` / `whisper-1`)
  2. **AWS Polly Neural** (`Engine="neural"`, `Joanna`, `Matthew`, `Kajal`)
  3. **Vaani.dev / VaaniStack** (multilingual and Indian English dialect speech models)
  4. **Universal Studio Neural Fallback** (`edge-tts` Microsoft Azure neural voices: Christopher, Jenny, Neerja, Prabhat, Ryan) with zero cost and no API keys required.
- **Audio-Reactive 3D Sphere Avatar**: Renders live pulsating waveforms and glows synchronized with interviewer speech and candidate voice input.
- **Real-Time Equalizer Waveform**: Visual decibel amplitude meter that bounces dynamically as you speak your technical answers.

### 3. Socratic Hint Ladder
- **Tier 1 — Directional Nudge**: Clarifying questions or high-level directional cues without naming data structures (5% score deduction).
- **Tier 2 — Algorithmic Pattern**: Identifies the optimal pattern or data structure (e.g. Two-Pointers, Hash Map, DP state representation) and why it fits (15% score deduction).
- **Tier 3 — Structural Pseudocode**: Provides structural pseudocode and step-by-step logic without writing finished code (30% score deduction).
- **Transparent Accountability**: Hint usage is factored into the rubric evaluation and detailed in the diagnostic report.

### 4. Self-Review & Self-Awareness Calibration
- **Turn-by-Turn Self Evaluation**: Candidates evaluate themselves on specific rubric dimensions for each question immediately following the interview.
- **Divergence Calibration Matrix**: Visual scatter chart comparing candidate self-perception against AI evaluator scoring to identify blind spots (over-confidence) and impostor syndrome (under-confidence).
- **Verbatim Transcript Replay**: Complete interactive transcripts showing strengths, weaknesses, rubric mappings, and actionable *"What you could have said better"* rewrites.

### 5. LeetCode-Style DSA Arena
- **Monaco Code Editor**: Split-screen technical coding IDE with syntax highlighting, indentation guides, and Dark/Light mode.
- **Multi-Language Sandbox**: Execute solutions in **Python 3.12**, **Java 21**, and **C++ 17**.
- **Codeforces API Integration**: Fetches real competitive programming problems dynamically filtered by difficulty rating (800 – 2400) and topic tags (DP, Binary Search, Trees, Graphs, Greedy, Two Pointers).
- **Clean Starter Boilerplates**: Problem boilerplate starter code is provided without leaking solutions.
- **Socratic Coding Hints**: Request calibrated algorithmic hints on demand during active coding.
- **Isolated Execution Engine**: Safe code runner powered by Bubblewrap (`bwrap`) / Docker sandbox with CPU timeouts, memory limits, and disabled network access.

### 6. AI-Assisted Coding Projects (Real-World System Projects)
- **Real-World Systems Engineering**: Practice with realistic architectural project problems:
  - **Distributed Rate Limiter**: Implement Token Bucket and Sliding Window algorithms with concurrent thread safety and Redis semantics.
  - **Async Task Queue with Dead Letter Queue**: Build priority job distribution, retry backoff, and failure isolation.
- **Multi-File Workspace**: Interactive tree explorer and code editor for realistic multi-module development.
- **Read-Only AI Copilot**: Guided AI assistant with strict read-only jailrails—explains concepts, troubleshoots errors, and reviews design without writing code directly for the candidate.
- **Automated CI/CD Test Runner**: Run complete Pytest test suites with real-time pass/fail assertions.
- **Prompt Quality Evaluator**: AI analysis of the candidate's prompts (clarity, specificity, context efficiency) with actionable recommendations on writing better engineering prompts.
- **Timed Project Mode**: 25-minute countdown clock simulating realistic live technical screens.

### 7. Planly — Adaptive Improvement Engine
- **Dynamic 7-Day Roadmaps**: Automatically generates multi-day learning plans addressing specific diagnostic weaknesses discovered during interviews.
- **Concrete Daily Tasks**: Practical balance of conceptual reading, coding challenges, system design exercises, and reassessments.
- **Curated Learning Resources**: Links to authoritative engineering documentation, RFCs, and high-signal engineering blogs.
- **Independent Learning Backlog**: Decoupled backlog of self-selected engineering topics to study outside scheduled plans.
- **Non-Mutating Plan Adaptation**: Preview new schedule adaptations before applying changes to preserve historical progress.

### 8. Dual-Cloud BYOC (Bring Your Own Cloud) & Cost Transparency
- **Dual Cloud Support**: Connect your own **Amazon Bedrock** or **Microsoft Azure OpenAI** account.
- **Zero Platform Markup**: Pay raw inference costs directly to AWS or Microsoft.
- **Automated IAM Policy Generator**: Generates least-privilege IAM policies scoped only to required foundation models (`bedrock:InvokeModel`).
- **Cryptographic Isolation**: Credentials encrypted at rest using AES-GCM / Fernet (`SKILLISSUE_SECRET_KEY`), decrypted in-memory only during validated requests, and never logged or leaked.
- **Live Cost & Credit Tracker**: Real-time header badge tracking tokens consumed, estimated USD cost, and configurable monthly token/spend ceiling limits.
- **Zero-Cost Offline Mode**: Built-in `MockProvider` enables 100% offline local development without AWS or Azure accounts.

### 9. Senior UI/UX Experience
- **Strict Light Theme**: Warm white surfaces (`#FAFAFA`, `#F4F4F5`, `#FFFFFF`), subtle borders (`#E4E4E7`), crisp dark text (`#09090B`), and restrained acid-lime and indigo accents.
- **Command Palette (`Cmd+K` / `Ctrl+K`)**: Quick navigation, instant session access, and system commands.
- **Rich Data Visualizations**: Recharts-powered radar skill charts, divergence delta bars, and historical competency trend lines.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Monaco Editor, Lucide React, Recharts, React Router v6 |
| **Backend** | Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async/sync), Alembic, LangChain, LangGraph |
| **Speech Engine** | Edge Neural TTS (Microsoft Azure neural network), Faster-Whisper, W3C MediaRecorder, Web Audio API |
| **Database** | PostgreSQL 16 (in Docker Compose, named volume `skillissue_pgdata`, port `5433`) |
| **Inference & BYOC** | Amazon Bedrock, Azure OpenAI Service, Vaani.dev, Built-in Offline Mock Provider |
| **Sandbox Execution** | Bubblewrap (`bwrap`) container isolation, isolated ephemeral processes, non-root user, no network |
| **Security** | Fernet AES-GCM credential encryption, JWT access/refresh tokens with versioning, CSP headers, rate-limiting |

---

## Quick Start (One Command)

The platform boots locally with a single command:

```bash
# Clone the repository
git clone https://github.com/enftaurus/skillissue.git
cd skillissue

# Launch PostgreSQL, apply migrations, and start Backend & Frontend
chmod +x dev.sh
./dev.sh
```

Once started:
- **Frontend Application**: [http://localhost:5173](http://localhost:5173)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **PostgreSQL Database**: `localhost:5433` (Database: `skillissue`)

### Useful CLI Commands

```bash
./dev.sh --check      # Verify dependencies, configs, and service connectivity
./dev.sh --stop       # Safely shut down all background services and containers
./dev.sh --reset-db   # Destroy local test database and re-migrate (requires confirmation)
```

---

## Testing & Quality Assurance

```bash
# Run all backend unit, integration, and security tests
PYTHONPATH=. backend/venv/bin/pytest backend/tests -v

# Run evaluator benchmarks
backend/venv/bin/python scripts/run_benchmarks.py

# Run Playwright Firefox cross-browser audio verification
backend/venv/bin/python scripts/verify_firefox_audio.py

# Build frontend production bundle
cd frontend && npm run build
```

---

## Architecture Decision Records (ADRs)

Every major architectural choice in Skill Issue is documented in [`docs/decisions/`](file:///home/rajababu/intern/skillissue/docs/decisions/):

- [`0001`](file:///home/rajababu/intern/skillissue/docs/decisions/0001-modular-monolith.md) — Modular Monolith Architecture
- [`0002`](file:///home/rajababu/intern/skillissue/docs/decisions/0002-provider-abstraction.md) — Model Provider Abstraction
- [`0003`](file:///home/rajababu/intern/skillissue/docs/decisions/0003-bedrock-byoc.md) — Amazon Bedrock BYOC Architecture
- [`0004`](file:///home/rajababu/intern/skillissue/docs/decisions/0004-postgresql-docker.md) — PostgreSQL in Docker Compose
- [`0005`](file:///home/rajababu/intern/skillissue/docs/decisions/0005-credential-encryption.md) — AES-GCM / Fernet Credential Encryption
- [`0006`](file:///home/rajababu/intern/skillissue/docs/decisions/0006-interview-engine-and-rubrics.md) — Multi-Category Rubric System
- [`0007`](file:///home/rajababu/intern/skillissue/docs/decisions/0007-coding-sandbox-architecture.md) — Sandboxed Code Execution
- [`0008`](file:///home/rajababu/intern/skillissue/docs/decisions/0008-planly-adaptive-engine.md) — Planly Adaptive Engine
- [`0009`](file:///home/rajababu/intern/skillissue/docs/decisions/0009-recommended-model-lineup.md) — Recommended Foundation Models
- [`0010`](file:///home/rajababu/intern/skillissue/docs/decisions/0010-docker-code-execution-service.md) — Docker Code Execution Service
- [`0011`](file:///home/rajababu/intern/skillissue/docs/decisions/0011-security-auth-session-and-judging-masking.md) — Security Architecture & Key Masking
- [`0012`](file:///home/rajababu/intern/skillissue/docs/decisions/0012-persistent-skills-verbatim-feedback-and-hints.md) — Persistent Skill Map, Socratic Hints & Planly Preview
- [`0013`](file:///home/rajababu/intern/skillissue/docs/decisions/0013-frontend-experience-and-design-system.md) — Design System & Calibrated Analytics
- [`0014`](file:///home/rajababu/intern/skillissue/docs/decisions/0014-langchain-langgraph-agent-architecture.md) — LangGraph Stateful Interview Agent
- [`0015`](file:///home/rajababu/intern/skillissue/docs/decisions/0015-reliability-audit-turn-idempotency-and-grounded-evaluations.md) — Turn Idempotency & Grounded Evaluations
- [`0016`](file:///home/rajababu/intern/skillissue/docs/decisions/0016-persistent-executor-learning-backlog-and-dsa-coaching.md) — Persistent Executor & DSA Coaching
- [`0017`](file:///home/rajababu/intern/skillissue/docs/decisions/0017-consolidated-bedrock-client-lifecycle-and-bounded-cache.md) — Bounded LRU Client Lifecycle Cache
- [`0018`](file:///home/rajababu/intern/skillissue/docs/decisions/0018-azure-openai-byoc-provider.md) — Azure OpenAI BYOC Provider
- [`0019`](file:///home/rajababu/intern/skillissue/docs/decisions/0019-cross-browser-cloud-neural-audio-tts-stt.md) — Cross-Browser Cloud Neural Audio (TTS & STT)

---

## Documentation Index

- [Architecture Overview](file:///home/rajababu/intern/skillissue/docs/architecture/overview.md)
- [Security Architecture](file:///home/rajababu/intern/skillissue/docs/architecture/security.md)
- [Architecture Decision Records (ADRs)](file:///home/rajababu/intern/skillissue/docs/decisions/README.md)
- [Codebase Knowledge Graph](file:///home/rajababu/intern/skillissue/docs/knowledge-graph/README.md)
- [AWS Bedrock Setup Guide](file:///home/rajababu/intern/skillissue/docs/product/aws-bedrock-setup.md)
- [Local Development Guide](file:///home/rajababu/intern/skillissue/docs/operations/local-development.md)
- [Agent Engineering Rules (`AGENTS.md`)](file:///home/rajababu/intern/skillissue/AGENTS.md)

---

## License & Usage

Skill Issue is engineered for students and software engineers. Evaluator scores are coaching estimates designed to provide diagnostic feedback, not guarantees of employment or corporate hiring decisions.
