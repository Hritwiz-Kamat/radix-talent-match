# RADIX Talent Match — Team Playbook (Scrum Master edition)

Today is **Sat 24 Oct 2026, launch day**. Hard deadline **Wed 28 Oct**. Presentations 29 Oct (Top 9), panels 30 Oct (Top 3), TGL Blitz 31 Oct.
Confidence tags: [Certain] from the brief, [Likely] strong inference, [Guessing] my judgement call.

---
## 1. The uncomfortable truths

1. **You have 4 build days, not 5.** The 28th is the deadline *and* the day you must be rehearsed. Real build time ends Tuesday night. [Certain]
2. **The brief says what wins: the live walkthrough.** Presentation = problem, architecture, live demo, one challenge you faced. A pretty UI with a failed demo loses to a plain UI that never breaks. [Certain]
3. **Q&A is 15 minutes of the 45** (30 present + 15 Q&A). If your team can't explain its own code, AI-generated code will not save you. Understanding is a *scored* skill here. [Certain on format; Likely on scoring weight]
4. **Integration is where hackathon teams die.** Roles 4 and 5 depend on Role 3. Roles 3, 4, 5 depend on the contract. Without a locked contract and mocks on Day 1, you will lose Monday. [Likely]
5. **The judges are the people who built Levels 1-5.** They care about *data quality and trustworthy generation* (the whole bootcamp theme). A team that shows validation gates, retries, and tests for its LLM output speaks their language. This is your cheapest differentiator. [Likely]
6. **Two things are missing from the pack: a scoring rubric, and `talent_check_company_skillsets.json`** (the zip has JDs, resumes, brief, checklist, event plan — no JSON). Ask the facilitator today. I built a clearly-labelled placeholder so Role 4 isn't blocked. [Certain]
7. **The milestone checklist says the walkthrough is "5-8 minutes"**, while the event plan/brief say 30 min + 15 min Q&A. They contradict each other. Confirm the real slot length with the facilitator before you rehearse. [Certain on the conflict]
8. **OpenRouter free models are rate-limited** [Likely: roughly 20 requests/min and about 50/day without purchased credit; more with credit — verify on openrouter.ai]. Your whole demo must therefore run from **pre-computed cached results**, committed to git. Buying ~$10 of credit as a team may be worth it as insurance — your call, not mine. [Guessing]

---
## 2. What the bootcamp guides actually meant (so you can answer questions)

| Bootcamp idea | One-line meaning | Where it appears in our project |
|---|---|---|
| Level 4: agent = prompt + provider + parser + sink | An "agent" is just: build a prompt, call an LLM, parse the answer into data, save it. | `core/extract.py` does exactly this for JDs and resumes. |
| Provider abstraction | Hide which LLM you use behind one function so you can swap it. | `core/llm.py`. If Gemini hits quota, change one line in `.env`. |
| Level 3: rules as tests | Write down "what good data looks like" as checks, run them automatically. | Our pytest tests + the quality gate in `extract.py`. |
| Level 5: gates + surgical retry | Validate output; if bad, retry *only the failed part*, with a limit. | `extract.py` retries up to 2 times, feeding the error back to the LLM. |
| Pydantic | Python classes that refuse malformed data. | `schemas.py` = the contract. |

You do **not** need LangGraph. A state machine would be over-engineering here. [Likely]

**Why not "structured output" APIs?** Many free OpenRouter models don't support tool-calling. So we ask for JSON as plain text, parse it, and validate it with Pydantic, retrying with the error message. That is exactly the Level 4 "parser" step plus the Level 5 "gate".

---
## 3. Architecture (what to draw on the slide)

```
 React UI (5 pages)  --HTTP-->  FastAPI backend
                                  |- jd_analytics   (LLM extract)  --> JD skill list ----------+
                                  |- resume_parsing (LLM extract)  --> Resume skill list       |
                                  |- profile_builder (plain code)  --> Candidate profile (JSON)|
                                  |- talent_check   (plain code)   --> readiness + 12 gaps     |
                                  '- skill_matching (rules + LLM)   --> match score + gap list <+
        shared: schemas.py (contract) | core/llm.py | core/extract.py (validate+retry+cache) | core/storage.py
                                         |
                                         v
                          SUPABASE: table `documents` (JSONB) + Storage bucket `candidate-files`
```

---
## 4. Schedule (adjust to your college hours)

**Sat 24 Oct (TODAY) — Lock & unblock**
- 9:30 launch. Form team, assign roles (see Section 6), confirm you are the Scrum Master.
- Ask facilitator: scoring rubric? sample JD/resume pack + `talent_check_company_skillsets.json`? any provided LLM keys? Does the facilitator supply a Supabase project, or do we create our own? (Supabase is mandatory — confirmed.)
- **You (SM), first 45 min — Supabase setup (mandatory):** (1) supabase.com -> New project (free tier is fine; pick the closest region). (2) SQL Editor -> paste `docs/supabase_schema.sql` -> Run. (3) Project Settings -> API: copy the Project URL and the **service_role** key. (4) Put them in your `backend/.env`, run `python scripts/seed_supabase.py` (must print `connected` and the pushed count). (5) Open Table Editor -> `documents` -> you should see the 4 candidate profiles. (6) Share the URL + service_role key with teammates **privately** (not in the repo, not in a public chat) — each person pastes them into their own `.env`. **Rotate the key after the hackathon.**
- **You (SM), by ~1:00 PM:** create the GitHub repo from this folder, push, add all 4 teammates. Everyone clones and runs `uvicorn app.main:app --reload` and sees `/api/health`.
- **Whole team, 1 hour:** read the brief, review `backend/app/schemas.py` together, argue changes, **lock v1.0**. Write the lock time in the team chat.
- The 4 sample candidate profiles are already built for you in `backend/data/store/profiles/`. Role 3 reviews them tonight.
- **Pre-warm the cache:** once keys work, Roles 1 and 2 run every JD and resume once and commit `backend/data/cache/`. That is your demo insurance.
- Everyone: endpoint returning mock data from `mocks.py` by tonight.
- Frontend shell: **you (SM) scaffold it tonight** with the Section 8 prompt, push it, and everyone just adds their page.

**Sun 25 — Real logic, standalone** Each role makes its module work for real against ≥2 sample files. Morning standup 10 min, evening check-in 10 min. Evening: every role demoes its module to the team on screen (not talks about it — runs it).

**Mon 26 — Integration day** Merge all branches into `main` by noon. Wire the 5-step flow end to end for one JD + one candidate. Expect it to break. Afternoon: fix; evening: all 4 candidates × all 6 JDs run without crashes (a script for this is Role 5's side task).

**Tue 27 — Polish & proof** Morning: UX polish, error messages, loading states, explanation text. Afternoon: tests green, **code freeze 6 PM** (only bug fixes after). Evening: full dress rehearsal with a timer. Record a **backup demo video** (screen recording) of the full flow.

**Wed 28 — Freeze & submit** No new features. Fresh-clone test on a *different laptop* (does `README` setup work?). Final rehearsal x2. Submit everything. Sleep.

**Thu 29 — Peer presentation** (30 min + 15 Q&A).

---
## 5. Scrum rituals (keep them tiny)

- **Standup, 10 min, twice/day** (morning + evening). Each person answers: Done? Next? Blocked?
- **Blocker rule:** stuck > 45 min → tell the SM in chat. Do not suffer silently.
- **Milestone tracker:** use `RADIX_Talent_Match_Milestone_Checklist.xlsx` from the pack; update after each standup: Not Started / In Progress / Blocked / Done. [Certain it exists per brief]
- **Dependency watch:** Roles 4 and 5 must never be waiting on Role 3 (brief says so explicitly). Fixture profiles solve this.
- **Known-bugs list:** one `docs/BUGS.md`; log bug, owner, status. Don't fix in chat and forget.

---
## 6. Roles — assign by strength, not by preference

**Recommended for you (Scrum Master): Role 2, Resume Parsing.** It is the lightest because the heavy part (`core/extract.py`) is already written; your job is a different prompt, the extras, testing on 4 resumes, and one React page. It is backend-flavoured, which matches your stack. [Likely]

**Don't guess who is strong — find out in 20 minutes.** Give everyone the same micro-task with their AI editor: *"Build a FastAPI endpoint that returns a list, and a React page that fetches and shows it."* Whoever finishes cleanly *and can explain it* is your React/Python lead. Put the quickest Python+prompting person on Role 1 or 5, the best frontend person on Role 3. The vanilla-JS teammate is a natural fit for **Role 3 (forms)** — React forms are the same DOM thinking — but only if the test confirms it. The SM scaffolds the React shell (Section 8) so Role 3 is not also blocked on setup.

| Role | Needs | Difficulty | Risk |
|---|---|---|---|
| 1 JD Analytics | LLM prompting, PDF/DOCX | Medium | Owns `core/extract.py` quality — Role 2 depends on it |
| 2 Resume Parsing | Same as 1, messier input | Medium | Messy layouts |
| 3 Profile Builder | React forms, CRUD | Easy backend / heavy frontend | Everyone depends on it; also the best candidate for the **React shell** |
| 4 Talent Check | Logic, scoring design, charts | Medium | Scoring design decisions → needs the most thinking |
| 5 Skill Matching | Fuzzy matching, LLM | Hardest | Quality of the gap list decides how impressive the demo feels |

Put your strongest coder on Role 5 or Role 1; put the best React person on Role 3. Roles 1 and 2 should pair closely — they share `extract.py`. If *you* hold a role with the Scrum Master job, pick the lightest one; Scrum work costs 1-2 hrs/day. [Likely]

---
## 7. How to use Antigravity without being lost

1. Everyone clones the repo; `AGENTS.md` is at the root. [Guessing: Antigravity picks up AGENTS.md; if not, paste it into the editor's rules/custom-instructions setting — I'm not certain of the exact config path.]
2. Each person opens `docs/ROLE_X_*.md` and pastes its **"Starter prompt"** section into the editor's chat.
3. **Always: plan first, then code.** Ask the AI "give me a 5-line plan, don't write code yet."
4. **After every chunk: "Explain what you just wrote, line by line, as if I'm a beginner."** Then close the explanation by saying it back in your own words.
5. **Small commits.** `git add . && git commit -m "role4: scoring function"` after each working step. Broken code is recoverable only if you committed the last working one.
6. **Run it yourself** after each step. If you didn't see it work, it doesn't work.
7. **Never paste secrets** into prompts.

---
## 8. Frontend shell (one prompt, one person, 1 hour)

Give this to the Role 3 owner's AI editor:

> Create a Vite React app in `frontend/`. Install react-router-dom and recharts. Create a left sidebar with 5 routes in this order: JD Analytics, Resume Parsing, Profile Builder, Talent Check, Skill Matching, each rendering a placeholder page in `src/pages/`. Add `src/api.js` exporting a `BASE = "http://localhost:8000"` and a small `get/post` helper that throws readable errors. Add a global "current candidate" and "current JD" context (React Context) so pages can share selections. Keep styling simple and clean. Don't add other libraries.

The shared "current candidate / current JD" context is what makes the 5 pages feel like *one tool* instead of five demos. That's an integration win.

---
## 9. What will make you win (in priority order)

1. **Flawless live flow** for ≥1 candidate/JD pair, with **cached fallbacks** so the demo survives a dead API. [Likely]
2. **Visibly different results** for the 4 candidates (a stated requirement) — build a "compare candidates" view on Talent Check (4 bars on one chart for one company). Judges see differentiation in 5 seconds. [Certain it's required; Likely it impresses]
3. **Gap list with actionable suggestions** ("learn X; do Y") — the brief explicitly says gap list > score. [Certain]
4. **Explainability on screen:** each score has a "why this score" panel (formula, evidence quote). It makes Q&A easy.
5. **Quality evidence:** a slide showing extraction tested against hand-labelled "golden" skills for the sample JDs (precision/recall), and the validate-retry gate. This is the Level 3-5 mindset. [Likely differentiator]
6. **Design decisions you can defend** — especially "what does *ready* mean numerically?" (the brief calls this out for Role 4).

Do NOT spend time on: auth/login, multiple typed Supabase tables / migrations (one JSONB table is enough and matches the brief's "JSON for most things"), animations, a chatbot, deployment to cloud. Run locally on one laptop with the backup video as insurance. [Guessing — deploy only if everything else is done Tue noon]

---
## 10. Presentation plan (Peer round: 30 min talk + 15 min Q&A)

| Min | Content |
|---|---|
| 0-3 | **Problem:** candidates apply blindly; they don't know their gaps. RADIX has company-side data; we flipped the lens. |
| 3-7 | **Architecture** on one slide; the shared contract; who built what. |
| 7-22 | **Live demo** — one story: Priya (entry-level) vs Google SWE → low match, clear gaps → switch to Oracle role → high match. Then show Rohan competitive everywhere. |
| 22-26 | **One challenge:** e.g. "LLM returned wrong categories/duplicates → we added a validation gate and retry loop with cached results." Show before/after. |
| 26-30 | Quality evidence + what we'd build next. |
| 30-45 | Q&A. |

Expert panel round is shorter (about 15 min [Likely — digits were stripped in the PDF text]); keep a **7-minute cut** of the same demo ready. Rehearse both with a timer.

**Q&A drill (each person must answer for their module):** What does your module take in / give out? Why LLM here and not plain code? What happens when the LLM returns garbage? How do you know it's correct? What would break first? How does your score differ between candidates and why? What did the AI write vs what did you decide?

---
## 10b. Supabase: how we use it, and what to say in the demo

- **What it is here:** one shared database for all five modules. Resume Parsing, JD Analytics and Profile Builder *write*; Talent Check and Skill Matching *read*. That is the integration story — not five apps passing files around.
- **Show it live:** in the demo, flip to the Supabase Table Editor after saving a profile and show the new row appear. 10 seconds, very convincing.
- **Why one JSONB table:** the brief says "Supabase — JSON for most things"; the contract objects are already JSON; one table keeps five people from fighting over migrations. Mention that production would use typed tables.
- **Safety:** RLS is on with no policies, so the public key can read nothing; only our backend's service_role key can. Keys live in `.env` only.
- **Shared-database etiquette (5 people, one project):** during development use candidate ids starting with `test-` for experiments; never delete the 4 sample profiles (re-run `seed_supabase.py` if someone does). Use `STORAGE_BACKEND=local` when you only need to work offline.
- **Resilience:** every write is mirrored to `backend/data/store/`; reads fall back to it if Supabase is unreachable. `/api/health` shows `connected` or the error. **Before every demo: open `/api/health` and read it.** If Supabase is down on stage, the app still runs from the mirror and you say so honestly.

---
## 11. Risk register

| Risk | Mitigation |
|---|---|
| LLM quota/API down during demo | Disk cache + provider switch in `.env` + backup video |
| Role 3 late | Fixture profiles from day 1; SM watches daily |
| Contract changes late | Locked v1.0; changes only via SM, with version bump and announcement |
| Merge conflicts | One folder per role; branches; daily merges |
| Someone can't explain their code | "Explain it to me" rule in AGENTS.md; Monday teach-back round |
| Supabase down / wrong key / free project paused (free projects can pause after a week of inactivity [Likely]) | `/api/health` check daily; local mirror fallback; seed script re-pushes everything; open the dashboard Mon and Tue to keep it awake |
| Scanned/odd PDFs | Offer DOCX version (the pack has both); clear error message |
| Overbuilding | Scope list in Section 9: "do NOT spend time on" |

---
## 12. Definition of done (from the brief) + our additions

- [ ] All 5 pieces run on their own against ≥2 sample JDs/resumes [Certain]
- [ ] 5 pieces wired into one flow end-to-end [Certain]
- [ ] Talent Check and Skill Matching give visibly different results for different candidates [Certain]
- [ ] All 4 candidates × 6 JDs run without crashing (our addition)
- [ ] README: fresh clone to running app in < 10 minutes (our addition)
- [ ] Backup demo video recorded (our addition)
- [ ] Every member can explain their module and the contract (our addition)
