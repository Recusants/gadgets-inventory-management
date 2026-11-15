# syntax=docker/dockerfile:1.4
# Dockerfile — Gadget Store System
#
# CACHE STRATEGY:
#   Layer 1: OS packages — cached until apt list changes
#   Layer 2: pip install — cached until requirements-docker.txt changes
#   Layer 3: COPY . .   — only this layer rebuilds on code changes
#   BuildKit cache mount — pip download cache persists across builds

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    netcat-traditional \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout=120 --retries=5 -r requirements-docker.txt

COPY . .

RUN mkdir -p /app/logs /app/media /app/staticfiles /app/tmp

# BUILD_HASH is injected at build time: docker build --build-arg BUILD_HASH=$(git rev-parse --short HEAD)
# The entrypoint uses APP_BUILD_HASH to detect new image versions reliably.
ARG BUILD_HASH=unknown
ENV APP_BUILD_HASH=${BUILD_HASH}

ENV DJANGO_SETTINGS_MODULE=config.settings.docker_prod
ENV PYTHONUNBUFFERED=1
ENV DEBUG=False
# Override worker count per-deployment via GUNICORN_WORKERS env var (default: auto)
ENV GUNICORN_WORKERS=0

RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "60", "--graceful-timeout", "30", "--worker-class", "sync", "config.wsgi:application"]
