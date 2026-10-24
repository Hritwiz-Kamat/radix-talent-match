# AGENTS.md — rules for every AI code editor on this team (Antigravity or otherwise)

Paste/keep this file at the repo root. If your editor does not read AGENTS.md automatically,
paste it into the editor's project rules / custom instructions.

## What we are building
**RADIX Talent Match** — a small end-to-end tool that tells a candidate how ready they are for a
specific job. Flow: `Pick a JD -> Parse a resume -> Build/update profile -> Talent Check -> Skill Matching`.
Five modules, five owners, one integrated app. Deadline: **Wed 28 Oct 2026**. Judged on a LIVE DEMO.

## Stack (do not change without asking the Scrum Master)
- Backend: Python 3.12, FastAPI, Pydantic v2, LangChain (only where an LLM genuinely helps)
- Frontend: React (Vite), plain `fetch`, Recharts for charts
- Storage: **Supabase is mandatory** (hackathon rule). All reads/writes go through `backend/app/core/storage.py` (`save/load/list_keys/upload_file`), which writes to Supabase (JSONB table `documents` + private bucket `candidate-files`) with a local mirror as fallback. Never call Supabase directly, never write SQL in a module, never put the Supabase key in React or git.
- LLM: **OpenRouter only**, ONLY via `backend/app/core/llm.py -> ask()` (it auto-falls-back across the free models listed in `.env`). Never create a model client anywhere else. Do NOT use tool-calling/structured-output APIs (free models often lack them): ask for JSON in plain text, parse, validate with Pydantic — see `core/extract.py`.

## Repo map
```
backend/app/schemas.py        <- THE DATA CONTRACT. Read it before writing any code.
backend/app/mocks.py          <- valid fake data for every contract object
backend/app/core/             <- llm.py (OpenRouter), extract.py (shared extractor), files.py, storage.py  (shared; do not fork)
backend/app/<your_module>/    <- YOUR code lives here, with a router.py exposing `router = APIRouter(...)`
backend/tests/                <- pytest. Every module ships tests.
frontend/src/pages/<Module>.jsx  <- YOUR page
docs/ROLE_*.md                <- your role brief
```

## Hard rules
1. **The contract is law.** All inputs/outputs of your module are the Pydantic models in `schemas.py`.
   If you think the contract is wrong, STOP and tell the Scrum Master. Never edit `schemas.py` yourself.
2. **Mock first.** Within the first hour, your endpoint must return valid mock data from `mocks.py`
   so other roles can integrate against it. Replace the mock with real logic afterwards.
3. **Plain code beats an LLM** wherever the logic is deterministic (scoring, forms, comparisons).
   Use an LLM only for extraction from messy text and fuzzy matching.
4. **Every LLM output is validated** by Pydantic and passes through a cheap quality gate before being used.
   Retry once or twice with the error message; never loop forever.
5. **Persist through `core/storage.py` only** — profiles, extracted skill lists and company levels must end up in Supabase so the 5 modules share one source of truth. Use `STORAGE_BACKEND=local` in `.env` only for offline solo work.
6. **Cache LLM results to disk** (see `core/extract.py`) and **commit `backend/data/cache/` to git**. Free OpenRouter models are rate-limited; the live demo must work with the Wi-Fi off.
7. **Errors are shown, not swallowed.** Return clear HTTP errors; the UI shows a human message.
8. **No secrets in git.** Keys only in `backend/.env`.
9. **Work on your own branch** (`role/<module>`), small commits, open a PR to `main`, Scrum Master merges.
10. **Do not touch other roles' folders.** Need a change there? Ask the owner.
11. Add `pytest` tests for your module. At least: one happy path, one bad-input path, one "different inputs give different outputs" test.

## Teaching rule (this matters for winning)
The human owner must be able to explain every file in their module to a judge. Therefore:
- Before writing code, give a 5-line plan and wait for approval.
- After writing code, explain it in plain English: what each function does and why. Use simple words.
- Prefer small, readable functions over clever ones. Add a short comment on every non-obvious line.
- When the human asks "why", answer fully; never just say "it works".

## Definition of done for any task
It runs, it has a test, the human can explain it, and it was exercised on at least 2 sample JDs/resumes.
