"""
Pre-warm Demo Cache (Phase 1.5).

Extracts and caches:
1. All 6 sample JDs (PDF)
2. All 4 sample Resumes (PDF)
3. 24 Skill Match evaluations (LLM tier ON, disk cache enabled)
4. Ensures disk cache contains all necessary evaluations
"""
import sys
import os
import re
from pathlib import Path

# Fix Windows console encoding
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from app.core import files, storage
from app.core.extract import extract_skills
from app.schemas import CandidateProfile, ExtractedSkillList
from app.skill_matching.matching import build_skill_match_result
from app.talent_check.scoring import load_company_levels_with_source, find_full_entry, score as score_tc

JDS_DIR = backend_dir / "data" / "jds"
RESUMES_DIR = backend_dir / "data" / "resumes"

JD_FILES = [
    ("Google LLC - Software Engineer.pdf", "Google LLC", "Software Engineer"),
    ("Google LLC - Data Scientist.pdf", "Google LLC", "Data Scientist"),
    ("Microsoft - Software Engineer.pdf", "Microsoft Corporation", "Software Engineer"),
    ("Microsoft - Data Analyst.pdf", "Microsoft Corporation", "Data Analyst"),
    ("Oracle - Application Support Analyst.pdf", "Oracle Financial Services Software", "Application Support Analyst"),
    ("Oracle - Associate Software Engineer.pdf", "Oracle Financial Services Software", "Associate Software Engineer"),
]

RESUME_FILES = [
    "Ananya Rao.pdf",
    "Karthik Subramaniam.pdf",
    "Priya Menon.pdf",
    "Rohan Verma.pdf",
]

JD_TASK_INSTRUCTIONS = (
    "Analyze this Job Description. Extract all technical and soft skills required "
    "by the employer. Pay special attention to determining whether the importance "
    "of each skill is 'required' or 'preferred'."
)

RESUME_TASK_INSTRUCTIONS = (
    "Analyze this candidate resume. Extract candidate name, email, education, "
    "experience, and all technical/soft skills with evidence quotes."
)


def main():
    print("=== PRE-WARMING DEMO CACHE ===")
    
    # 1. Warm JDs
    print("\n--- 1. Processing 6 Sample JDs ---")
    extracted_jds = {}
    for filename, company, role in JD_FILES:
        filepath = JDS_DIR / filename
        if not filepath.exists():
            print(f"Skipping missing JD: {filename}")
            continue
        raw_text = files.read_text(filepath.read_bytes(), filename)
        jd_res = extract_skills(
            text=raw_text,
            source_type="jd",
            source_file=filename,
            company=company,
            role=role,
            task_instructions=JD_TASK_INSTRUCTIONS,
            use_cache=True,
        )
        storage.save("jd", filename, jd_res)
        extracted_jds[filename] = jd_res
        source = jd_res.extras.get("source", "llm") if jd_res.extras else "llm"
        print(f"  [OK] {filename}: {len(jd_res.skills)} skills extracted (source: {source})")

    # 2. Warm Resumes
    print("\n--- 2. Processing 4 Sample Resumes ---")
    for filename in RESUME_FILES:
        filepath = RESUMES_DIR / filename
        if not filepath.exists():
            print(f"Skipping missing Resume: {filename}")
            continue
        raw_text = files.read_text(filepath.read_bytes(), filename)
        res_skills = extract_skills(
            text=raw_text,
            source_type="resume",
            source_file=filename,
            task_instructions=RESUME_TASK_INSTRUCTIONS,
            use_cache=True,
        )
        storage.save("resume", filename, res_skills)
        source = res_skills.extras.get("source", "llm") if res_skills.extras else "llm"
        print(f"  [OK] {filename}: {len(res_skills.skills)} skills extracted (source: {source})")

    # Load canonical fixture profiles from storage
    CANDIDATE_IDS = ["ananya-rao", "karthik-subramaniam", "priya-menon", "rohan-verma"]
    profiles = {cid: CandidateProfile.model_validate(storage.load("profiles", cid)) for cid in CANDIDATE_IDS}

    # 3. Warm 24 Skill Matches & Talent Checks
    print("\n--- 3. Pre-computing 24 Matrix Combinations ---")
    levels, tc_source = load_company_levels_with_source()
    match_count = 0

    for filename, company, role in JD_FILES:
        jd_res = extracted_jds.get(filename)
        if not jd_res:
            continue
        tc_entry = find_full_entry(company, role, levels)

        for cand_id, profile in profiles.items():
            # A. Skill Match
            match_res = build_skill_match_result(
                candidate_id=cand_id,
                jd_source_file=filename,
                candidate_skills=profile.skills,
                job_skills=jd_res.skills,
                use_llm=True,
                use_cache=True,
            )
            canon_jd = Path(filename).stem.lower().replace(" ", "-").replace("_", "-")
            storage.save("results", f"match-{cand_id}-{canon_jd}", match_res)

            # B. Talent Check
            if tc_entry:
                tc_res = score_tc(
                    profile,
                    tc_entry["levels"],
                    company,
                    company_aggregates=tc_entry.get("aggregate"),
                    role_weights_used=tc_entry.get("weights_used"),
                    data_source=tc_source,
                )
                result_key = re.sub(r"[^a-z0-9]+", "-", f"{cand_id}-{company}-{role}".lower()).strip("-")
                storage.save("results", result_key, tc_res)

            match_count += 1
            print(f"  [OK] [{match_count}/24] {profile.name} vs {company} - {role}: SM {match_res.match_score}%, TC {tc_res.readiness_score if tc_entry else 'N/A'}%")

    print("\n=== CACHE PRE-WARMING COMPLETE ===")


if __name__ == "__main__":
    main()
