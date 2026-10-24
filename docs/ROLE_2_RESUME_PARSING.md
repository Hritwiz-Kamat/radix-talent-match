# ROLE 2 — Resume Parsing (LLM extraction)

**Mission:** upload a resume (PDF/DOCX) -> skills + reliable extras (education, projects, experience).
**In:** file bytes. **Out:** `ExtractedSkillList` with `source_type="resume"` and `extras={"education":..., "projects":[...], "experience":[...]}`. **Hands off to:** Role 3 (pre-fills the profile).
Read `AGENTS.md` and `backend/app/schemas.py` first. **Pair with Role 1 today** — you share `core/extract.py`; agree who edits it (Role 1 owns it; you request changes).

## Endpoints (`backend/app/resume_parsing/router.py`, prefix `/api/resume`)
- `GET  /api/resume/samples`
- `POST /api/resume/parse` (multipart) / `POST /api/resume/parse-sample?name=...` -> `ExtractedSkillList`; save with `storage.save("resume", ...)` (lands in Supabase, kind `resume`). Uploaded resume files: `storage.upload_file(f"resume/{filename}", bytes)`.

## Build order
1. (60 min) Return `mocks.MOCK_RESUME`.
2. (2 hrs) Real flow with `RESUME_INSTRUCTIONS`: *"This is a resume. Extract technical skills with evidence from projects, internships, coursework and certifications. Confidence: high = used in a project/job with detail; medium = listed with context; low = only listed in a skills list. Do not invent skills."* For `extras`, make a second structured call (small Pydantic model: education str, projects list, experience list) — keep it separate from skills so one failure doesn't kill both.
3. (2 hrs) Resumes are messy: two-column PDFs scramble text order. Test all 4 resumes in PDF *and* DOCX. If PDF text is garbled, fall back to the DOCX version and show a clear message.
4. (1.5 hrs) **Contrast test:** the 4 candidates are deliberately different (Ananya = systems generalist, Karthik = data analyst, Priya = entry-level/support, Rohan = all-rounder). Test that the extracted skill sets differ in the expected way. Hand-label 8 expected skills per resume; test recall.
5. React page `ResumeParsing.jsx`: upload -> skill chips by category with evidence -> button **"Create/Update profile from this resume"** that routes to Profile Builder with pre-fill.

## Done when
All 4 resumes parse (PDF + DOCX); extras populated; pre-fill button works; golden test passes.

## You must be able to explain
Why do resumes need more tolerance than JDs? What does `confidence` mean here? How do you stop the model inventing skills?

## Starter prompt
> Read AGENTS.md, backend/app/schemas.py and backend/app/core/extract.py. I own Role 2 (Resume Parsing). Give me a 5-line plan first. Then build backend/app/resume_parsing/router.py per docs/ROLE_2_RESUME_PARSING.md using core/extract.py, returning mocks.MOCK_RESUME first. Don't edit core/ or schemas.py; tell me if you think they need a change. Explain each step simply.
