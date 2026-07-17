#!/bin/sh
# ─────────────────────────────────────────────────────────────────
#  docker-entrypoint.sh — Instant BI entrypoint
#  Starts the service specified by the SERVICE env variable.
# ─────────────────────────────────────────────────────────────────
set -e

case "${SERVICE:-all}" in
  fastapi)
    echo "Starting FastAPI backend on port 8000 ..."
    exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
    ;;
  frontend)
    echo "Starting Nginx (React frontend) on port 80 ..."
    nginx -g "daemon off;"
    ;;
  all)
    echo "Starting FastAPI backend + Nginx (React frontend) ..."

    # Fix nginx config: replace 'backend:8000' with 'localhost:8000' for single-container
    sed -i 's/http:\/\/backend:8000/http:\/\/localhost:8000/g' /etc/nginx/conf.d/default.conf

    # Start nginx in the background
    nginx

    # Start FastAPI in the foreground (so container stays alive)
    uvicorn backend.main:app --host 0.0.0.0 --port 8000
    ;;
  *)
    echo "Unknown service: ${SERVICE}"
    echo "Valid values: fastapi, frontend, all (default)"
    exit 1
    ;;
esac
