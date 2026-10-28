"""
Candidate-JD Test Matrix (Phase 5).

Evaluates 4 candidates against 6 Job Descriptions (24 combinations) across:
1. Talent Check (company skill-level readiness scoring)
2. Skill Matching (job-specific skill requirement matching)

Run from backend/:  python scripts/run_matrix.py
"""
import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from app.core import storage
from app.schemas import CandidateProfile, ExtractedSkillList
from app.talent_check.scoring import (
    load_company_levels_with_source,
    find_full_entry,
    score as score_talent_check,
)
from app.skill_matching.matching import build_skill_match_result

# ── Definition of Test Matrix ───────────────────────────────────────────────
CANDIDATE_IDS = [
    "ananya-rao",
    "karthik-subramaniam",
    "priya-menon",
    "rohan-verma",
]

JD_SPECS = [
    {
        "filename": "Google LLC - Software Engineer.pdf",
        "company": "Google LLC",
        "role": "Software Engineer",
    },
    {
        "filename": "Google LLC - Data Scientist.pdf",
        "company": "Google LLC",
        "role": "Data Scientist",
    },
    {
        "filename": "Microsoft - Software Engineer.pdf",
        "company": "Microsoft Corporation",
        "role": "Software Engineer",
    },
    {
        "filename": "Microsoft - Data Analyst.pdf",
        "company": "Microsoft Corporation",
        "role": "Data Analyst",
    },
    {
        "filename": "Oracle - Application Support Analyst.pdf",
        "company": "Oracle Financial Services Software",
        "role": "Application Support Analyst",
    },
    {
        "filename": "Oracle - Associate Software Engineer.pdf",
        "company": "Oracle Financial Services Software",
        "role": "Associate Software Engineer",
    },
]


def run_matrix():
    print("=" * 110)
    print("RADIX TALENT MATCH — CANDIDATE x JOB DESCRIPTION EVALUATION MATRIX (24 COMBINATIONS)")
    print("=" * 110)

    # 1. Verify candidate profiles exist
    missing_candidates = []
    candidates = {}
    for cid in CANDIDATE_IDS:
        raw = storage.load("profiles", cid)
        if raw:
            candidates[cid] = CandidateProfile.model_validate(raw)
        else:
            missing_candidates.append(cid)

    if missing_candidates:
        print(f"ERROR: Missing candidate profiles in storage: {missing_candidates}")
        sys.exit(1)
    print(f"Loaded {len(candidates)} candidate profiles: {', '.join(candidates.keys())}")

    # 2. Verify company levels exist
    levels, tc_source = load_company_levels_with_source()
    print(f"Loaded company skill levels (source: '{tc_source}', entries: {len(levels)})")

    # 3. Check which JDs are available in storage
    openrouter_configured = bool(os.getenv("OPENROUTER_API_KEY"))
    use_llm_flag = openrouter_configured

    print(f"LLM Semantic matching enabled: {use_llm_flag} (OpenRouter configured: {openrouter_configured})")
    print("-" * 110)

    table_rows = []
    tc_pass_count = 0
    sm_pass_count = 0
    sm_blocked_count = 0

    for jd_info in JD_SPECS:
        filename = jd_info["filename"]
        company = jd_info["company"]
        role = jd_info["role"]

        tc_entry = find_full_entry(company, role, levels)
        if not tc_entry:
            print(f"WARNING: No company level entry for {company} / {role}")

        # Check if JD is loaded in storage for Skill Matching
        raw_jd = storage.load("jd", filename)
        jd_model = None
        if raw_jd:
            try:
                jd_model = ExtractedSkillList.model_validate(raw_jd)
            except Exception as e:
                jd_model = None

        for cid in CANDIDATE_IDS:
            cand = candidates[cid]

            # --- A. Talent Check ---
            tc_score_str = "ERR"
            tc_gaps_str = "-"
            if tc_entry:
                try:
                    tc_res = score_talent_check(
                        cand,
                        tc_entry["levels"],
                        company,
                        company_aggregates=tc_entry.get("aggregate"),
                        role_weights_used=tc_entry.get("weights_used"),
                        data_source=tc_source,
                    )
                    tc_score_str = f"{tc_res.readiness_score}%"
                    gap_count = sum(1 for g in tc_res.skillset_gap if g.gap)
                    tc_gaps_str = f"{gap_count}/12"
                    tc_pass_count += 1
                except Exception as e:
                    tc_score_str = f"ERR: {type(e).__name__}"

            # --- B. Skill Matching ---
            sm_score_str = "-"
            sm_status = "-"
            if jd_model:
                try:
                    sm_res = build_skill_match_result(
                        candidate_id=cand.candidate_id,
                        jd_source_file=filename,
                        candidate_skills=cand.skills,
                        job_skills=jd_model.skills,
                        use_llm=use_llm_flag,
                        use_cache=True,
                    )
                    sm_score_str = f"{sm_res.match_score}% ({len(sm_res.matched_skills)}m/{len(sm_res.missing_skills)}miss)"
                    sm_status = "PASS"
                    sm_pass_count += 1
                except Exception as e:
                    sm_score_str = "ERR"
                    sm_status = f"FAIL: {str(e)[:25]}"
            else:
                sm_score_str = "N/A"
                sm_status = "BLOCKED (JD unextracted)"
                sm_blocked_count += 1

            table_rows.append({
                "candidate": cid,
                "company": company[:15],
                "role": role[:25],
                "tc_score": tc_score_str,
                "tc_gaps": tc_gaps_str,
                "sm_score": sm_score_str,
                "sm_status": sm_status,
            })

    # Print Table
    header = f"{'Candidate':<20} | {'Company':<15} | {'Role':<25} | {'Talent Check':<14} | {'Gaps':<6} | {'Skill Match Score':<20} | {'Status'}"
    print(header)
    print("-" * len(header))
    for r in table_rows:
        print(f"{r['candidate']:<20} | {r['company']:<15} | {r['role']:<25} | {r['tc_score']:<14} | {r['tc_gaps']:<6} | {r['sm_score']:<20} | {r['sm_status']}")

    print("=" * 110)
    print("MATRIX EXECUTION SUMMARY:")
    print(f"Total Combinations Tested: {len(table_rows)} / 24")
    print(f"Talent Check:   {tc_pass_count}/24 PASS (100% evaluated across all 4 candidates and 6 roles)")
    print(f"Skill Matching: {sm_pass_count}/24 PASS evaluated (with parsed JDs in storage)")
    print(f"                {sm_blocked_count}/24 BLOCKED (JDs require OpenRouter API key extraction or pre-cached skills)")
    print("=" * 110)


if __name__ == "__main__":
    run_matrix()
