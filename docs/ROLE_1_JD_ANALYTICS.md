# ROLE 1 — JD Analytics (LLM extraction)  *(Also owns the shared extractor quality)*

**Mission:** upload a JD (PDF/DOCX) -> structured skill list mapped to the 12 RADIX categories.
**In:** file bytes. **Out:** `ExtractedSkillList` with `source_type="jd"` (`schemas.py`). **Hands off to:** Role 5 (Skill Matching).
Read `AGENTS.md` and `backend/app/schemas.py` first.

## Endpoints (in `backend/app/jd_analytics/router.py`, `router = APIRouter(prefix="/api/jd")`)
- `GET  /api/jd/samples` -> list of JD files in `backend/data/jds/`
- `POST /api/jd/analyze` (multipart file) OR `POST /api/jd/analyze-sample?name=...` -> `ExtractedSkillList`; also `storage.save("jd", source_file, result)` so Role 5 can load it by `jd_source_file` — this lands in Supabase (kind `jd`). Uploaded JD files: `storage.upload_file(f"jd/{filename}", bytes)`.
- `GET  /api/jd/{source_file}` -> a previously analysed JD.

## Build order
1. (60 min) Router returns `mocks.MOCK_JD`. Push. Frontend can integrate now.
2. (2 hrs) Real flow: `core/files.read_text` -> `core/extract.extract_skills(task_instructions=JD_INSTRUCTIONS, ...)`. Write `JD_INSTRUCTIONS`: *"This is a job description. Skill signal is concentrated in 'Key Responsibilities' and 'What We're Looking For' — start there. Mark `importance='required'` for must-haves and 'preferred' for nice-to-haves. Also extract company and role if stated."* Parse company/role: ask the LLM, or a second tiny structured call.
3. (2 hrs) Run all 6 sample JDs. Read each result. Fix the prompt where it misses prose-implied skills (e.g. "design scalable services" -> SYSD).
4. (1.5 hrs) **Golden test:** for each JD, hand-write 8-10 skills it *must* find in `tests/golden_jd.json`; test recall >= 80%. This is your "quality evidence" slide.
5. React page `JDAnalytics.jsx`: pick sample or upload; skills grouped by category with confidence chips and evidence on hover; a bar chart of skills per category; "Use this JD" button that sets the shared current JD.

## Done when
Works on all 6 sample JDs; result cached; golden test passes; page shows skills + evidence; a bad file gives a readable error.

## You must be able to explain
Why an LLM instead of keyword matching? What does the validation gate catch? What is cached and why? How did you decide `required` vs `preferred`?

## Starter prompt (paste into your AI editor)
> Read AGENTS.md and backend/app/schemas.py. I own Role 1 (JD Analytics). First give me a 5-line plan. Then create backend/app/jd_analytics/router.py with the endpoints in docs/ROLE_1_JD_ANALYTICS.md, returning mocks.MOCK_JD first. Do not edit schemas.py or core/. After each step, explain the code to me in simple words.
