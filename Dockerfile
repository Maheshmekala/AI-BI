# ─────────────────────────────────────────────────────────────────
#  Dockerfile for Instant BI
#  Build with:  docker build -t instant-bi .
#
#  Run (serves React frontend + FastAPI backend via Nginx):
#    docker run -p 3000:80 instant-bi
#
#  Run backend only:
#    docker run -p 8000:8000 -e SERVICE=fastapi instant-bi
# ─────────────────────────────────────────────────────────────────

# ================================================================
# Stage 1 — Build the React + Vite frontend
# ================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ .
RUN npm run build

# ================================================================
# Stage 2 — Install Python dependencies (into a throw-away image)
# ================================================================
FROM python:3.11-slim AS python-builder

WORKDIR /app

# Install system build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt backend/requirements.txt ./

# Install all Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r backend/requirements.txt && \
    pip install --no-cache-dir python-multipart

# ================================================================
# Stage 3 — Final runtime image
# ================================================================
FROM python:3.11-slim

WORKDIR /app

# ── Install runtime system packages ──
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx-light \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ── Copy Python packages from builder stage ──
COPY --from=python-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-builder /usr/local/bin /usr/local/bin

# ── Copy built frontend assets ──
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

# ── Copy nginx config ──
COPY nginx.conf /etc/nginx/conf.d/default.conf

# ── Copy application source code ──
COPY . /app

# ── Create required directories ──
RUN mkdir -p /app/uploads /app/data

# ── Environment variables ──
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SERVICE=all

# ── Expose ports ──
EXPOSE 8000 80

# ── Health check ──
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -sf http://localhost:8000/api/health || exit 1

# ── Entrypoint ──
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
