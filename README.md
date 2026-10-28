# RADIX Talent Match

End-to-end talent readiness platform: JD Analytics -> Resume Parsing -> Profile Builder -> Talent Check -> Skill Matching.

## Quick Start

### 1. Backend Setup (Python 3.12 + uv)
```bash
cd backend

# Create virtual environment and install dependencies using uv
uv venv
uv pip install -r requirements.txt

# Configure environment variables (NEVER commit .env to git)
cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY, SUPABASE_URL, and SUPABASE_SERVICE_KEY
# For offline solo work, set STORAGE_BACKEND=local (uses local JSON mirror in data/store/)

# (Optional, if using Supabase) Seed database with candidate profiles and company skill levels:
uv run python scripts/seed_supabase.py

# Run the test suite (73 passing tests):
uv run python -m pytest -q

# Run candidate-JD evaluation matrix (24 combinations):
uv run python scripts/run_matrix.py

# Start the FastAPI server (http://localhost:8000):
uv run uvicorn app.main:app --reload --port 8000
```

- **Health check**: `http://localhost:8000/api/health` (reports contract version and storage connection status)
- **Interactive API Docs**: `http://localhost:8000/docs`

### 2. Frontend Setup (React + Vite)
```bash
cd frontend
npm install
npm run build
npm run dev      # http://localhost:5173
```

---

## Environment Variables (.env)
Create `backend/.env` based on `backend/.env.example`:
- `OPENROUTER_API_KEY`: API key for OpenRouter models (used by JD Analytics and LLM semantic matching).
- `OPENROUTER_MODELS`: Comma-separated list of OpenRouter models to fall back across.
- `SUPABASE_URL`: Your Supabase project URL (`https://<project-ref>.supabase.co`).
- `SUPABASE_SERVICE_KEY`: Supabase service role key (backend only, never in frontend).
- `STORAGE_BACKEND`: `supabase` (default) or `local` (offline fallback to `backend/data/store/`).

*Note: Environment credentials must remain local and are excluded by `.gitignore`.*

---

## Module Status Overview

| Module | Backend Status | Frontend Status | Implementation Type | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **JD Analytics** | Verified (HTTP 200) | Placeholder | Real Backend / Cached Offline | Parses PDF JDs with PyPDFLoader; extracts skills via shared LLM pipeline; caches to `data/cache/`. |
| **Resume Parsing** | Verified (HTTP 200) | Placeholder | Mock-based | Validates and stores uploaded resumes; returns structured `MOCK_RESUME` output. |
| **Profile Builder** | Verified (HTTP 200) | Verified (Full UI) | Real Implementation | Full CRUD for candidate profiles, CV upload, prefill from parsed resume. |
| **Talent Check** | Verified (HTTP 200) | Verified (Full UI) | Real Implementation | Deterministic 12-skillset readiness scoring, role weights, radar chart, multi-candidate comparison. |
| **Skill Matching** | Verified (HTTP 200) | Placeholder | Real Backend | 4-tier engine (exact, alias, fuzzy, semantic with safe fallback); match matrix endpoint. |
