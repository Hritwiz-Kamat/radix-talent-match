# ROLE 3 — Profile Builder (plain code; everyone depends on you)

**Mission:** let a candidate build and edit a full profile; save/load it as JSON.
**In:** form entry, ideally pre-filled from Role 2. **Out:** `CandidateProfile`. **Hands off to:** Roles 4 and 5.
**You are the critical path.** Priority 1 is a working save/load loop, even with dummy data.

## Endpoints (`backend/app/profile_builder/router.py`, prefix `/api/profile`)
- `GET  /api/profile` -> list of candidate_ids (+ names)
- `GET  /api/profile/{candidate_id}` -> `CandidateProfile`
- `PUT  /api/profile/{candidate_id}` (body `CandidateProfile`) -> validates (Pydantic does it) and saves via `storage.save("profiles", id, p)`
- `POST /api/profile/prefill` (body `ExtractedSkillList` from resume) -> a draft `CandidateProfile` (not saved)
- `POST /api/profile/{candidate_id}/cv` (multipart) -> `storage.upload_file(...)` (Supabase Storage), set `cv_file` to the returned path

## Build order
1. **Already done for you:** the 4 hand-labelled sample profiles are in `backend/data/store/profiles/` (built by `scripts/build_fixture_profiles.py`). Read the script — it is also your answer key for what a *good* resume extraction looks like. Check them against the resume PDFs and fix anything you disagree with (tell the SM).
2. Router with the 4 endpoints above. Save/load works.
3. Also (side task, 1 hr) build the **React shell** (see Playbook Section 8) — you're the natural owner.
4. React page `ProfileBuilder.jsx`: sections for basics, skills (add / remove / edit category + confidence), hackathons, internships, certifications, preferred roles, CV upload. Inline validation messages. A profile picker at the top that sets the shared "current candidate".
5. Persistence is already wired: `storage.save/load/list_keys` talk to Supabase (table `documents`) for you. Your job is to prove it works from the UI: save a profile, then check the row in the Supabase Table Editor. CV uploads go through `storage.upload_file(f"cv/{candidate_id}/{filename}", bytes, content_type)` (private bucket `candidate-files`).

## Done when
Create, edit, reload a profile; all 4 samples load; pre-fill from resume works; invalid input shows an error, not a crash.

## You must be able to explain
Why `candidate_id` is the key. How validation works (Pydantic). Why one JSONB table in Supabase is enough for this demo and what you'd change for production (typed tables, auth, row-level security per user).

## Starter prompt
> Read AGENTS.md and backend/app/schemas.py. I own Role 3 (Profile Builder) and the React shell. Give me a 5-line plan. First write a script that creates the 4 sample candidate profile JSON files in backend/data/store/profiles using the CandidateProfile model (I'll give you each resume's skills). Then build the router per docs/ROLE_3_PROFILE_BUILDER.md. Explain each step simply.
