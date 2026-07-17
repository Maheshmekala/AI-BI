# Docker Setup Guide for Instant BI

This guide explains how to build and run the Instant BI application using Docker.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (v20.10+)
- `.env` file with your API keys (see [Configuration](#configuration))

## Quick Start

### 1. Build and Run with Docker Compose

```bash
# Build the unified image
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

The application will be available at:
- **Frontend (React)**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### 2. Run with Docker (single service)

```bash
# Build the unified image
docker build -t instant-bi .

# Run FastAPI backend + React frontend (default)
docker run -p 8000:8000 -p 3000:80 instant-bi

# Run backend only
docker run -p 8000:8000 -e SERVICE=fastapi instant-bi

# Run React frontend only (served by Nginx)
docker run -p 80:80 -e SERVICE=frontend instant-bi
```

## Configuration

### Environment Variables

Create a `.env` file in the project root with your API keys:

```env
# LLM Configuration
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
GOOGLE_API_KEY=your_google_key_here

# Optional: Database connections
# DATABASE_URL=postgresql://user:pass@db:5432/dbname
```

Pass environment variables to Docker:

```bash
docker run -p 8000:8000 -p 3000:80 --env-file .env instant-bi
```

## File Structure

| File | Purpose |
|------|---------|
| `Dockerfile` | Unified multi-stage build (frontend + backend) |
| `docker-compose.yml` | Orchestrates the unified container |
| `nginx.conf` | Frontend proxy configuration for React build |
| `docker-entrypoint.sh` | Entrypoint script for multi-service support |
| `.dockerignore` | Files to exclude from build context |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│               Single Container                       │
│                                                      │
│  ┌──────────┐  ┌──────────────────┐                  │
│  │ FastAPI  │  │ Nginx (React SPA)│                  │
│  │ :8000    │  │ :80 → :3000      │                  │
│  └──────────┘  └──────────────────┘                  │
│                                                      │
│  DuckDB (embedded, in-memory or file-based)          │
│                                                      │
└─────────────────────────────────────────────────────┘
```

Choose service via `SERVICE` env var: `all` (default), `fastapi`, or `frontend`.

## Volume Mounts

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `./data` | `/app/data` | Sample and persistent data files |
| `./uploads` | `/app/uploads` | User-uploaded files |

## Health Checks

The container includes a health check that runs every 30 seconds:

```bash
docker-compose ps
```

## Troubleshooting

### Container exits immediately

```bash
# View logs
docker-compose logs

# Common issues:
# - Missing API key: ensure .env file is properly configured
# - Port conflicts: change ports in docker-compose.yml
```

### Port conflicts

If ports 8000 or 3000 are already in use:

```yaml
# In docker-compose.yml, change:
ports:
  - "8001:8000"    # API on 8001
  - "3001:80"      # Frontend on 3001
```

### Rebuild without cache

```bash
docker-compose build --no-cache
```

## Useful Commands

```bash
# Build and start in background
docker-compose up -d --build

# Follow logs for all services
docker-compose logs -f

# Execute command in running container
docker exec -it instant-bi bash

# View running processes
docker-compose ps

# Remove all containers
docker-compose down

# Remove images too
docker-compose down --rmi all
```

---

For issues or questions, check the main [README.md](README.md) or open an issue on GitHub.
