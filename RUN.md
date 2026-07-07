# Instant BI — How to Run

## Backend (FastAPI)

```cmd
cd d:\BI
venv\Scripts\activate.bat
pip install fastapi uvicorn python-multipart
uvicorn backend.main:app --reload --port 8000
```

The API will be at `http://localhost:8000/api/health`

## Frontend (Vite + React + TypeScript)

```cmd
cd d:\BI\frontend
npm install
npm run dev
```

The app will be at `http://localhost:3000`

## Architecture

- `backend/` — FastAPI REST API (wraps existing Python code)
- `frontend/` — Vite + React + TypeScript + Tailwind CSS
- Frontend proxies `/api/*` to the backend (configured in `vite.config.ts`)
