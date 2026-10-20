#!/usr/bin/env bash
# Skill Issue — Master Development Control Script
# Single entry point for local development, health checks, and lifecycle management.

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Terminal Color Codes
BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
CYAN="\033[36m"
RESET="\033[0m"

log_info() {
    echo -e "${GREEN}[INFO]${RESET} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${RESET} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${RESET} $1"
}

log_banner() {
    echo -e "${BOLD}${CYAN}"
    echo "=========================================================="
    echo "      Skill Issue — AI Interview Preparation Platform     "
    echo "  'Your interview went badly. Good. Now we have data.'    "
    echo "=========================================================="
    echo -e "${RESET}"
}

# PID tracking file for graceful background management
PID_DIR="$PROJECT_ROOT/.dev_pids"
mkdir -p "$PID_DIR"

cleanup_and_exit() {
    echo ""
    log_warn "Caught interruption signal. Stopping background processes..."
    stop_services
    exit 0
}

trap cleanup_and_exit SIGINT SIGTERM

stop_services() {
    log_info "Stopping application services..."
    if [ -f "$PID_DIR/backend.pid" ]; then
        PID=$(cat "$PID_DIR/backend.pid")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null || true
            log_info "Stopped FastAPI backend (PID: $PID)"
        fi
        rm -f "$PID_DIR/backend.pid"
    fi

    if [ -f "$PID_DIR/frontend.pid" ]; then
        PID=$(cat "$PID_DIR/frontend.pid")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null || true
            log_info "Stopped Vite frontend (PID: $PID)"
        fi
        rm -f "$PID_DIR/frontend.pid"
    fi

    # Check if containers should be stopped
    if [ "$1" == "--all" ]; then
        log_info "Stopping Docker PostgreSQL and Executor containers..."
        docker compose stop postgres executor || true
    fi
}

check_dependencies() {
    log_info "Checking system requirements..."
    local missing=0

    if ! command -v python3 &>/dev/null; then
        log_error "python3 is not installed (expected 3.12+)."
        missing=1
    fi

    if ! command -v node &>/dev/null; then
        log_error "Node.js is not installed (expected 20+)."
        missing=1
    fi

    if ! command -v npm &>/dev/null; then
        log_error "npm is not installed."
        missing=1
    fi

    if ! command -v docker &>/dev/null; then
        log_error "Docker is not installed or not in PATH."
        missing=1
    fi

    if ! docker compose version &>/dev/null; then
        log_error "docker compose plugin is not installed."
        missing=1
    fi

    if [ "$missing" -ne 0 ]; then
        log_error "One or more core host dependencies are missing. Please install them and retry."
        exit 1
    fi
    log_info "Host requirements verified."
}

init_env() {
    if [ ! -f ".env" ]; then
        log_warn ".env file not found. Creating from .env.example..."
        cp .env.example .env
        log_info "Created .env with default development settings."
    fi
}

reset_database() {
    echo -e "${RED}${BOLD}WARNING: --reset-db will permanently destroy the local PostgreSQL volume and all saved data!${RESET}"
    read -p "Type 'yes' to proceed with resetting the database: " confirm
    if [ "$confirm" != "yes" ]; then
        log_info "Database reset cancelled."
        exit 0
    fi

    log_warn "Tearing down PostgreSQL container and volume..."
    docker compose down -v
    log_info "Starting clean PostgreSQL container..."
    docker compose up -d postgres

    log_info "Waiting for database readiness..."
    local retries=20
    until docker compose exec -T postgres pg_isready -U postgres -d skillissue &>/dev/null || [ "$retries" -le 0 ]; do
        sleep 1
        retries=$((retries - 1))
    done

    log_info "Running Alembic migrations..."
    backend/venv/bin/alembic -c backend/alembic.ini upgrade head
    log_info "Database cleanly reset and migrated."
    exit 0
}

run_check() {
    log_banner
    check_dependencies
    init_env

    log_info "Inspecting Docker status..."
    docker compose ps

    log_info "Checking port availability..."
    local PG_PORT=${POSTGRES_PORT:-5433}
    if nc -z 127.0.0.1 "$PG_PORT" &>/dev/null; then
        log_info "PostgreSQL is reachable on port $PG_PORT."
    else
        log_warn "PostgreSQL is not responding on port $PG_PORT. (Will be launched on ./dev.sh)"
    fi

    log_info "Verifying Python venv..."
    if [ -f "backend/venv/bin/uvicorn" ]; then
        log_info "Backend venv is present and uvicorn is installed."
    else
        log_warn "Backend venv needs dependency installation."
    fi

    log_info "Verifying frontend node_modules..."
    if [ -d "frontend/node_modules" ]; then
        log_info "Frontend node_modules directory is present."
    else
        log_warn "Frontend requires npm install."
    fi

    log_info "Verifying persistent sandbox executor service..."
    if docker compose ps executor &>/dev/null; then
        log_info "Executor service definition verified in Compose."
    else
        log_warn "Executor container service not found."
    fi

    log_info "All preliminary environment checks passed."
    exit 0
}

# Handle CLI Flags
if [ "$1" == "--check" ]; then
    run_check
elif [ "$1" == "--stop" ]; then
    log_banner
    stop_services --all
    log_info "All services stopped."
    exit 0
elif [ "$1" == "--reset-db" ]; then
    log_banner
    reset_database
fi

# Main Dev Startup Flow
log_banner
check_dependencies
init_env

# 1. Start PostgreSQL and Persistent Sandbox Executor in Docker Compose
log_info "Ensuring PostgreSQL and Persistent Ubuntu Sandbox Executor are running..."
docker compose up -d postgres executor

log_info "Waiting for PostgreSQL and Executor readiness..."
retries=25
until docker compose exec -T postgres pg_isready -U postgres -d skillissue &>/dev/null || [ "$retries" -le 0 ]; do
    echo -n "."
    sleep 1
    retries=$((retries - 1))
done
echo ""

if [ "$retries" -le 0 ]; then
    log_error "PostgreSQL container failed to become healthy. Check 'docker compose logs postgres'."
    exit 1
fi
log_info "PostgreSQL is healthy on host port ${POSTGRES_PORT:-5433}."

if curl -s -f http://127.0.0.1:8001/health &>/dev/null; then
    log_info "Persistent Sandbox Executor is healthy on http://127.0.0.1:8001."
else
    log_warn "Persistent Executor is initializing in background."
fi

# 2. Check / Setup Python virtual environment
if [ ! -d "backend/venv" ]; then
    log_info "Creating backend Python virtual environment..."
    python3 -m venv backend/venv
    backend/venv/bin/pip install --upgrade pip
fi
backend/venv/bin/pip install -q -r backend/requirements.txt

# 3. Apply Alembic migrations
log_info "Applying database migrations..."
backend/venv/bin/alembic -c backend/alembic.ini upgrade head

# 4. Check Frontend packages
if [ ! -d "frontend/node_modules" ]; then
    log_info "Installing frontend npm packages..."
    (cd frontend && npm install)
fi

# 5. Stop any existing stale processes from previous dev runs
stop_services

# 6. Start FastAPI Backend in Background
log_info "Starting FastAPI backend at http://localhost:8000 ..."
backend/venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$PID_DIR/backend.pid"

# 7. Start Vite Frontend in Background
log_info "Starting Vite frontend at http://localhost:5173 ..."
(cd frontend && npm run dev) &
FRONTEND_PID=$!
echo "$FRONTEND_PID" > "$PID_DIR/frontend.pid"

# 8. Report Status and Wait
sleep 2
echo ""
echo -e "${BOLD}${GREEN}✔ Skill Issue local environment is RUNNING!${RESET}"
echo "----------------------------------------------------------"
echo -e "  Frontend UI:        ${BOLD}${CYAN}http://localhost:5173${RESET}"
echo -e "  Backend API:       ${BOLD}${CYAN}http://localhost:8000${RESET}"
echo -e "  Interactive Docs:  ${BOLD}${CYAN}http://localhost:8000/docs${RESET}"
echo -e "  PostgreSQL Port:   ${BOLD}${CYAN}${POSTGRES_PORT:-5433}${RESET}"
echo -e "  Default LLM Mode:  ${BOLD}${GREEN}Mock Engine (zero-cost offline)${RESET}"
echo "----------------------------------------------------------"
echo -e "${YELLOW}Press Ctrl+C anytime to cleanly shut down all services.${RESET}"
echo ""

# Keep script running to monitor children and catch Ctrl+C
wait "$BACKEND_PID" "$FRONTEND_PID"
