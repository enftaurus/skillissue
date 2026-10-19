# Local Development Guide — Skill Issue

## 1. Quick Start

Skill Issue provides a single-command local setup script:

```bash
chmod +x dev.sh
./dev.sh
```

The script manages:
1. Verifying system dependencies (Python 3.12+, Node 20+, Docker).
2. Generating `.env` from `.env.example` if not already present.
3. Starting PostgreSQL 16 container via Docker Compose (using port 5433 by default to avoid conflicts).
4. Waiting for PostgreSQL to pass its healthcheck.
5. Applying Alembic database migrations.
6. Launching the FastAPI backend at `http://localhost:8000`.
7. Launching the Vite React frontend at `http://localhost:5173`.

---

## 2. CLI Options

The `./dev.sh` script supports several diagnostic and lifecycle flags:

```bash
# Verify environment without starting services
./dev.sh --check

# Gracefully stop all background services and containers
./dev.sh --stop

# Reset database (requires interactive confirmation 'yes')
./dev.sh --reset-db
```

---

## 3. Manual Component Execution (Alternative)

If you prefer running services in separate terminal tabs:

### PostgreSQL
```bash
docker compose up -d postgres
```

### Backend
```bash
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt
alembic -c backend/alembic.ini upgrade head
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 4. Offline Development with Mock Provider

You do NOT need real AWS credentials to develop or test Skill Issue. By default, the system operates with the built-in `MockProvider`, which generates realistic responses, parses JD skills, simulates follow-ups, and scores rubrics instantly without cost.

When ready to test live AWS Bedrock inference:
1. Register an account at `http://localhost:5173`.
2. Navigate to **Provider Settings**.
3. Follow the one-page setup guide at `/docs/aws-bedrock-setup`.
4. Enter your AWS Access Key, Secret Key, and preferred region (e.g. `us-east-1`).
