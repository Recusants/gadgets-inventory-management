#!/usr/bin/env bash
# ==============================================================================
# 21 VOID TECHNOLOGIES — Quick Launch Controller (Linux / macOS)
# Modes: local (default), docker_dev, docker_prod
# Usage: ./launch.sh [mode]
# ==============================================================================

set -e

MODE="${1:-local}"

echo "============================================================================"
echo "  21 VOID TECHNOLOGIES — Record Keeping System"
echo "  Mode: ${MODE}"
echo "============================================================================"

open_url() {
    local url="$1"
    sleep 2
    if command -v xdg-open > /dev/null; then
        xdg-open "$url"
    elif command -v open > /dev/null; then
        open "$url"
    else
        echo "Please open $url in your web browser."
    fi
}

if [ "$MODE" = "local" ]; then
    echo "[1/4] Checking Python environment..."
    if [ ! -f "venv/bin/python" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv venv
    fi

    echo "[2/4] Activating environment and installing dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt --quiet

    echo "[3/4] Applying SQLite migrations..."
    python manage.py migrate --settings=config.settings.local

    echo "[4/4] Starting Django development server..."
    open_url "http://127.0.0.1:8000/" &
    python manage.py runserver 127.0.0.1:8000 --settings=config.settings.local

elif [ "$MODE" = "docker_dev" ]; then
    echo "Starting Docker Development Stack (Live Reload, PostgreSQL 16)..."
    docker compose -f docker-compose.dev.yml up --build

elif [ "$MODE" = "docker_prod" ]; then
    echo "Starting Docker Production Stack (Gunicorn + Nginx + PostgreSQL 16)..."
    docker compose -f docker-compose.prod.yml up -d --build
    open_url "http://localhost/" &
    echo "Production stack is online. Run 'docker compose -f docker-compose.prod.yml logs -f' to view logs."

else
    echo "[ERROR] Unknown mode: '${MODE}'"
    echo "Valid options: local, docker_dev, docker_prod"
    exit 1
fi
