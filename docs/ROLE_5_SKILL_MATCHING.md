# ROLE 5 — Skill Matching (fuzzy match; hardest, biggest demo impact)

**Mission:** how well does a candidate match ONE specific JD, with a score and an *actionable gap list*. The brief says the gap list matters more than the number.
**In:** `CandidateProfile` (or resume list) + one JD `ExtractedSkillList` (saved by Role 1 via `storage`, kind `jd`, in Supabase); load candidates with `storage.load("profiles", id)`; save each result with `storage.save("results", f"match-{candidate_id}-{jd}", result)` so the matrix survives restarts. **Out:** `SkillMatchResult`.

## Endpoints (`backend/app/skill_matching/router.py`, prefix `/api/skill-match`)
- `POST /api/skill-match` body `{candidate_id, jd_source_file}` -> `SkillMatchResult`
- `GET  /api/skill-match/matrix` -> all candidates x all analysed JDs (scores only) — your integration smoke test AND a demo slide.

## Matching design (tiered: cheap and explainable first, LLM only for leftovers)
1. **Normalise** names (lowercase, strip punctuation/versions: "Node.js" -> "nodejs"). Exact match -> `match_type="exact"`, similarity 1.0.
2. **Alias map** (small dict you maintain: "js"->"javascript", "postgres"->"postgresql", "ml"->"machine learning") -> `alias`.
3. **Fuzzy** with `rapidfuzz` (token_set_ratio >= 88) -> `fuzzy`.
4. **LLM adjudication for the leftovers only:** ONE batched structured call: "Given these unmatched JD skills and these candidate skills, return which pairs are the same or clearly equivalent, with a 0-1 similarity." Accept >= 0.7 -> `semantic`. Cache it. If the LLM fails, fall back to steps 1-3 (never crash).
5. **Score:** required skills weight 2, preferred weight 1, unspecified 1. `match_score = round(100 * Σ weight(matched) / Σ weight(all))`. Optional: partial credit 0.5 if the candidate has a *different skill in the same category*.
6. **Gap list:** every unmatched JD skill as `MissingSkill`, sorted required-first, then by category; add a one-line `suggestion` (LLM batch call or a template: "Build a small project using {skill}"). Show *why* each matched skill matched.

## Build order
1. (60 min) Mock endpoint. 2. (2 hrs) Steps 1-3 + scoring as pure functions with tests. 3. (2 hrs) LLM step + cache + fallback. 4. (1.5 hrs) Test: Priya vs Oracle roles > Priya vs Google SWE; Ananya vs Google SWE > Ananya vs Data Scientist; etc. 5. React page: pick candidate + JD (shared context), big score, matched list with match-type badges, **prioritised missing list with suggestions**. 6. Side task: the matrix script (4 candidates x 6 JDs) that must run without errors — run it daily from Monday.

## Done when
Scores differ sensibly across candidates; gap list is prioritised and has suggestions; works with the LLM off; matrix runs clean.

## You must be able to explain
Why tiered matching? What does each match_type mean? What does the LLM do and what happens if it's down? Why weight required skills double?

## Starter prompt
> Read AGENTS.md and backend/app/schemas.py. I own Role 5 (Skill Matching). Give me a 5-line plan first. Then implement tiered matching per docs/ROLE_5_SKILL_MATCHING.md as pure, tested functions (exact -> alias -> rapidfuzz -> one batched LLM call via core/llm.py, with fallback). Return mocks.MOCK_MATCH from the router first. Explain simply after each step.
