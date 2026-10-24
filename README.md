# RADIX Talent Match
Start here: `docs/00_TEAM_PLAYBOOK.md`, then your `docs/ROLE_*.md`. AI editors read `AGENTS.md`.

## Run backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add OPENROUTER_API_KEY + SUPABASE_URL + SUPABASE_SERVICE_KEY
# one person (the SM) runs docs/supabase_schema.sql in the Supabase SQL editor first
python scripts/seed_supabase.py   # pushes profiles + company levels; must say 'connected'
uvicorn app.main:app --reload     # http://localhost:8000/api/health  (shows Supabase status)  and /docs
pytest -q
```
## Run frontend
```bash
cd frontend && npm install && npm run dev      # http://localhost:5173
```
Sample JDs are in `backend/data/jds/`, resumes in `backend/data/resumes/`, 4 hand-labelled candidate profiles in `backend/data/store/profiles/`. `backend/data/talent_check_company_skillsets.PLACEHOLDER.json` is a GUESSED stand-in until the real file arrives.
