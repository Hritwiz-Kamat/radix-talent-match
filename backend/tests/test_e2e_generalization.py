"""
End-to-End Generalization Test for RADIX Talent Match.

Verifies the complete five-module workflow for a completely unseen candidate
and a synthetic custom Job Description without relying on predefined fixtures.

Flow:
  1. JD Upload & Analysis -> /api/jd-analytics/upload
  2. Unseen Resume Upload & Parsing -> /api/resume/parse
  3. Candidate Profile Creation & Persistence -> /api/profile/prefill
  4. Talent Check Readiness Evaluation -> /api/talent-check
  5. Multi-tier Skill Matching -> /api/skill-match
  6. Storage Persistence & Matrix Verification -> /api/skill-match/matrix
"""
import io
import os
import pytest
from fastapi.testclient import TestClient

os.environ["STORAGE_BACKEND"] = "local"

from app.core import storage
from app.main import app
from app.schemas import CandidateProfile, ExtractedSkillList, SkillMatchResult, TalentCheckResult


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    from app.core import storage
    monkeypatch.setattr(storage, "supabase_enabled", lambda: False)
    return TestClient(app)


SYNTHETIC_JD_TEXT = """Job Title: Systems & Cloud Architect
Company: Apex Cloud Labs
Overview:
We are looking for a Systems & Cloud Architect to lead our distributed infrastructure.

Required Skills:
- Strong proficiency in Rust or Go required for low-latency engine development.
- Deep expertise in Distributed Systems and System Design required.
- Hands-on experience with Docker and Kubernetes required.
- Proficiency in PostgreSQL and SQL database management required.
- Strong problem solving and data structures knowledge required.

Preferred Skills:
- Experience with C++ and Linux kernel concepts preferred.
- Familiarity with Machine Learning pipelines preferred.
"""

SYNTHETIC_RESUME_TEXT = """ELENA ROSTOVA
elena.rostova@techmail.io | +1 555 019 2834 | Seattle, WA
LinkedIn: https://linkedin.com/in/elena-rostova | GitHub: https://github.com/erostova

PROFESSIONAL SUMMARY
Systems and Cloud Engineer with deep expertise in distributed backends, high-throughput microservices, and Kubernetes infrastructure.

EDUCATION
Master of Science in Computer Science, University of Washington, 2022

TECHNICAL COMPETENCIES
Languages: Rust, Go, Python
Cloud & DevOps: Docker, Kubernetes, AWS, CI/CD
Databases: PostgreSQL, Redis, SQL
Architecture: Distributed Systems, System Design, Microservices, Data Structures, Algorithms

PROFESSIONAL EXPERIENCE
Senior Backend Engineer | CloudScale Inc. (2022 - Present)
- Designed distributed data processing engine in Rust and Go handling 100k requests/second.
- Deployed containerized microservices to Kubernetes clusters on AWS with automated CI/CD.
- Optimized PostgreSQL database schema and complex analytical queries.
"""


def test_full_workflow_unseen_candidate_and_custom_jd(client):
    # -------------------------------------------------------------------------
    # Step 1: Upload and Analyze a brand new Job Description
    # -------------------------------------------------------------------------
    jd_filename = "Apex_Cloud_Labs_Architect.txt"
    jd_bytes = io.BytesIO(SYNTHETIC_JD_TEXT.encode("utf-8"))
    files = {"file": (jd_filename, jd_bytes, "text/plain")}

    jd_res = client.post("/api/jd-analytics/upload", files=files)
    assert jd_res.status_code == 200, f"JD Upload failed: {jd_res.text}"
    jd_data = jd_res.json()

    extracted_jd = ExtractedSkillList.model_validate(jd_data)
    assert extracted_jd.source_file == jd_filename
    assert len(extracted_jd.skills) >= 4
    jd_skill_names = [s.skill_name.lower() for s in extracted_jd.skills]
    assert any("rust" in s for s in jd_skill_names)
    assert any("distributed" in s for s in jd_skill_names)

    # Verify dynamic listing includes the new JD
    list_res = client.get("/api/jd-analytics/list")
    assert list_res.status_code == 200
    available_jds = list_res.json()
    assert any(j["source_file"] == jd_filename for j in available_jds)

    # -------------------------------------------------------------------------
    # Step 2: Upload and Parse an unseen Candidate Resume
    # -------------------------------------------------------------------------
    resume_filename = "Elena_Rostova_Resume.txt"
    resume_bytes = io.BytesIO(SYNTHETIC_RESUME_TEXT.encode("utf-8"))
    res_files = {"file": (resume_filename, resume_bytes, "text/plain")}

    resume_res = client.post("/api/resume/parse", files=res_files)
    assert resume_res.status_code == 200, f"Resume parse failed: {resume_res.text}"
    resume_data = resume_res.json()

    extracted_resume = ExtractedSkillList.model_validate(resume_data)
    assert extracted_resume.source_file == resume_filename
    assert len(extracted_resume.skills) >= 4
    # Verify candidate identity was extracted genuinely (NOT mock data)
    assert extracted_resume.extras.get("name") == "Elena Rostova"
    assert extracted_resume.extras.get("email") == "elena.rostova@techmail.io"
    resume_skill_names = [s.skill_name.lower() for s in extracted_resume.skills]
    assert any("rust" in s for s in resume_skill_names)
    assert any("kubernetes" in s for s in resume_skill_names)

    # -------------------------------------------------------------------------
    # Step 3: Create and Persist Candidate Profile
    # -------------------------------------------------------------------------
    prefill_res = client.post("/api/profile/prefill?save=true", json=resume_data)
    assert prefill_res.status_code == 200, f"Prefill failed: {prefill_res.text}"
    profile_data = prefill_res.json()

    profile = CandidateProfile.model_validate(profile_data)
    assert profile.name == "Elena Rostova"
    assert profile.candidate_id == "elena-rostova"
    assert profile.email == "elena.rostova@techmail.io"

    # Verify candidate is saved in storage and appears in /api/profile
    profiles_list = client.get("/api/profile").json()
    assert any(p["candidate_id"] == "elena-rostova" for p in profiles_list)

    # -------------------------------------------------------------------------
    # Step 4: Run Talent Check for the new candidate
    # -------------------------------------------------------------------------
    tc_res = client.post(
        "/api/talent-check",
        json={
            "candidate_id": "elena-rostova",
            "company": "Google LLC",
            "role": "Software Engineer",
        },
    )
    assert tc_res.status_code == 200, f"Talent check failed: {tc_res.text}"
    tc_data = tc_res.json()
    tc_result = TalentCheckResult.model_validate(tc_data)
    assert tc_result.candidate_id == "elena-rostova"
    assert 0 <= tc_result.readiness_score <= 100
    assert len(tc_result.skillset_gap) > 0

    # -------------------------------------------------------------------------
    # Step 5: Run Skill Matching (Candidate + Custom JD)
    # -------------------------------------------------------------------------
    match_res = client.post(
        "/api/skill-match",
        json={
            "candidate_id": "elena-rostova",
            "jd_source_file": jd_filename,
        },
    )
    assert match_res.status_code == 200, f"Skill matching failed: {match_res.text}"
    match_data = match_res.json()
    match_result = SkillMatchResult.model_validate(match_data)
    assert match_result.candidate_id == "elena-rostova"
    assert match_result.jd_source_file == jd_filename
    assert 0 < match_result.match_score <= 100
    assert len(match_result.matched_skills) > 0

    # Check matched skills contain Rust or Docker
    matched_names = [m.jd_skill.lower() for m in match_result.matched_skills]
    assert any("rust" in m or "docker" in m or "distributed" in m for m in matched_names)

    # -------------------------------------------------------------------------
    # Step 6: Verify Matrix and Persistence
    # -------------------------------------------------------------------------
    matrix_res = client.get("/api/skill-match/matrix")
    assert matrix_res.status_code == 200
    matrix_entries = matrix_res.json().get("matrix", [])
    entry = next(
        (
            e
            for e in matrix_entries
            if e["candidate_id"] == "elena-rostova" and e["jd_source_file"] == jd_filename
        ),
        None,
    )
    assert entry is not None, "Match result was not recorded in matrix!"
    assert entry["match_score"] == match_result.match_score

    # Verify stored document
    stored = storage.load("results", f"match-elena-rostova-{jd_filename}")
    assert stored is not None
    assert stored["match_score"] == match_result.match_score
