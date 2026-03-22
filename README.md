# etl-stats-server

ET:Legacy match stats API and UI (FastAPI + SQLite + Vite/React).

## Run

**Backend** (from `backend/`):

```bash
cp .env.example .env   # set STATS_API_TOKEN and optional DATABASE_URL / CORS_ORIGINS
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Settings are read from `backend/.env` (path is fixed relative to the app package, so it works whether you start uvicorn from `backend/` or the repo root).

**Frontend** (from `frontend/`):

```bash
cp .env.example .env    # optional: set VITE_API_PROXY if the API is not on port 8000
npm install && npm run dev
```

The dev server proxies `/api` to `VITE_API_PROXY` or `http://127.0.0.1:8000` by default. If something else is using 8000, run the API on another port (e.g. `--port 8010`) and set `VITE_API_PROXY=http://127.0.0.1:8010` in `frontend/.env` or `.env.local`.

**Ingest:** `POST /api/submit-stats` with header `Authorization: Bearer <STATS_API_TOKEN>` and JSON body shaped like `refs/sample_simple.json`.

**Tests:** `cd backend && .venv/bin/python -m pytest tests/ -v`
