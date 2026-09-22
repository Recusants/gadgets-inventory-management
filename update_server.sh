#!/usr/bin/env bash
# ==============================================================================
# 21 Void Technologies - One-Command Server Deployment & Update
# ==============================================================================
set -e

echo "=== Pulling latest Docker image from Docker Hub ==="
docker compose -f docker-compose.deploy.yml pull

echo "=== Starting/Restarting Containers ==="
docker compose -f docker-compose.deploy.yml up -d

echo "=== Running Database Migrations ==="
docker compose -f docker-compose.deploy.yml exec web python manage.py migrate --settings=config.settings.docker_prod

echo "=== Server is Live and Running at http://127.0.0.1:8086 ==="
