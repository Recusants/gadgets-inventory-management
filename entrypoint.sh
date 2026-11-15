#!/bin/bash
# entrypoint.sh — Gadget Store System
# Optimized: skips makemigrations entirely, only runs collectstatic when image changes

set -e

echo "========================================"
echo "  Gadget Store System - Starting"
echo "========================================"

TARGET_HOST="${POSTGRES_HOST:-${DB_HOST:-db}}"
TARGET_PORT="${POSTGRES_PORT:-${DB_PORT:-5432}}"

echo "Waiting for database at $TARGET_HOST:$TARGET_PORT..."
while ! nc -z "$TARGET_HOST" "$TARGET_PORT"; do sleep 0.5; done
echo "[OK] Database is ready!"

# Generate a fingerprint using the build-time git SHA (injected via Dockerfile ARG BUILD_HASH).
# Falls back to manage.py mtime for images built without the ARG.
CURRENT_HASH="${APP_BUILD_HASH:-$(stat -c %Y /app/manage.py 2>/dev/null || echo "unknown")}"
MARKER_FILE="/app/staticfiles/.image_hash"

# Check if this is a new image / first boot
NEEDS_SETUP=false
if [ ! -f "$MARKER_FILE" ]; then
    NEEDS_SETUP=true
    echo "[INFO] First boot detected — full setup required."
elif [ "$(cat $MARKER_FILE 2>/dev/null)" != "$CURRENT_HASH" ]; then
    NEEDS_SETUP=true
    echo "[INFO] Image change detected — running migrations and static files."
else
    echo "[OK] Same image as last boot — skipping migrations and collectstatic."
fi

SETTINGS="${DJANGO_SETTINGS_MODULE:-config.settings.docker_prod}"

echo "Running database migrations ($SETTINGS)..."
python manage.py migrate --noinput --settings="$SETTINGS"
echo "[OK] Migrations up to date!"

if [ "$NEEDS_SETUP" = true ]; then
    if [ "$DEBUG" = "True" ] || [ "$DEBUG" = "true" ] || [ "$DEBUG" = "1" ]; then
        echo "Dev mode: skipping collectstatic for instant startup"
    else
        echo "Collecting static files ($SETTINGS)..."
        python manage.py collectstatic --noinput --no-post-process --settings="$SETTINGS" --ignore "*.ts" --ignore "*.scss" --ignore "*.less" --ignore "*.md"
        echo "[OK] Static files collected!"
    fi

    # Write marker so next restart is instant
    mkdir -p /app/staticfiles
    echo "$CURRENT_HASH" > "$MARKER_FILE"
fi

echo ""
echo "  Gadget Store System is ready"
echo "========================================"

# Dynamic worker count: use GUNICORN_WORKERS if set to > 0, otherwise auto-calculate (2×cores)+1 capped at 4
if [ "${GUNICORN_WORKERS:-0}" -gt 0 ] 2>/dev/null; then
    WORKERS="$GUNICORN_WORKERS"
else
    WORKERS=$(python -c "import os; print(min((os.cpu_count() or 1) * 2 + 1, 4))")
fi

if [ "$1" = "gunicorn" ]; then
    echo "[INFO] Starting Gunicorn with $WORKERS workers..."
    exec "$@" --workers "$WORKERS"
else
    exec "$@"
fi
