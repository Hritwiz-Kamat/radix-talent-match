# ROLE 4 — Talent Check (plain code; scoring design)

**Mission:** one button: candidate profile vs a company's expected bar across all 12 skillsets -> readiness score + per-skillset gaps.
**In:** `CandidateProfile` + company name. **Out:** `TalentCheckResult` (`schemas.py`). No LLM needed.
Data: **the real `talent_check_company_skillsets.json` was NOT in the zip** — the SM is asking the facilitator. Until it arrives use `backend/data/talent_check_company_skillsets.PLACEHOLDER.json` (levels are *guesses* made from the JD text). Company levels live in Supabase as `storage.load("company_skillsets", "all")` (seeded from the placeholder/real file by `scripts/seed_supabase.py`; re-seed when the real file arrives). Write a small `load_company_levels()` adapter so swapping in the real file's shape is a 10-minute job. **Step 0 when the real file lands:** print its shape and tell the SM.

## Endpoints (`backend/app/talent_check/router.py`, prefix `/api/talent-check`)
- `GET  /api/talent-check/companies`
- `POST /api/talent-check` body `{candidate_id, company}` -> `TalentCheckResult`
- `GET  /api/talent-check/compare?company=...` -> results for all saved candidates (powers the comparison chart)

## The design decision (the brief says this matters): what does "ready" mean?
Proposed v1 — *simple, explainable, defensible* [Guessing: calibrate with the 4 candidates]:
1. **candidate_level per category** (0-10) — *tested against the 4 sample candidates + placeholder levels*: take the **strongest skill** in that category (high=7, medium=5, low=3) and add **+1 per additional skill in the same category (max +3)**; cap at 10; no skills -> 0. `OTHER` is not one of the 12 skillsets: ignore it in scoring. (An earlier "sum of small weights" version FAILED calibration — scores were compressed to 12-49 and Ananya barely separated from Karthik on data roles. Don't go back to it.)
2. **gap** = `candidate_level < required_level`; `gap_size = max(0, required - candidate)`.
3. **readiness_score** = `round(100 * Σ min(candidate, required) / Σ required)` over the 12 skillsets (so exceeding the bar in one skillset can't hide a gap in another).
4. Put the formula in `scoring_method`, and an `explanation` per category ("3 skills: Python(high), Java(high), C++(medium) -> 6.25 -> 6").
Known weakness: resumes rarely evidence `APTI` and `COMM`, so every candidate scores ~0 there. Decide how to treat it (e.g. exclude categories with zero evidence for *all* candidates, or show it as 'not assessable') — this is a good 'design decision' story for the panel.
Alternative to discuss: weight categories by how critical they are for the role. Decide, write it down, defend it.

## Build order
1. (60 min) Mock endpoint. 2. (2 hrs) Scoring function as a **pure Python function** `score(profile, company_levels) -> TalentCheckResult` — easy to test. 3. (1.5 hrs) **Calibration tests** (my check with the placeholder levels already passes: Ananya 69-70 on SWE vs 33-37 on data roles; Karthik 52-53 on data vs 27 on SWE; Priya's best is Oracle Application Support (46); Rohan highest everywhere (68-80). Re-check once the real JSON arrives.) in `tests/test_talent_check.py` encoding the brief's stated fits, e.g.: Ananya > Karthik for Google SWE; Karthik > Ananya for Google Data Scientist; Priya > her own Google score at Oracle roles; Rohan competitive everywhere. If tests fail, tune weights — not the tests. 4. (2 hrs) React page: company picker, big readiness number, radar chart (candidate vs required, Recharts), gap table sorted by gap_size, "why this score" panel, and **compare-candidates** bar chart.

## Done when
Different candidates give visibly different results; calibration tests pass; formula visible in UI; works for all 6 roles.

## You must be able to explain
Your formula and why. Why min(candidate, required)? What would change your weights? Why is this plain code, not an LLM?

## Starter prompt
> Read AGENTS.md and backend/app/schemas.py. I own Role 4 (Talent Check). First, inspect talent_check_company_skillsets.json and tell me its structure. Then give me a 5-line plan. Implement a pure function score(profile, company_levels) per docs/ROLE_4_TALENT_CHECK.md, with pytest calibration tests, then the router, then the page with Recharts. Explain simply after each step.
