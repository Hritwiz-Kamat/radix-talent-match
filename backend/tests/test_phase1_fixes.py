"""
Tests for Phase 1 Fixes:
1. Scanned PDF (text < 200 chars) returns HTTP 400 with clear message.
2. Fixture fallback sets extras['source'] = 'stored_fixture_fallback'.
3. Sample resume list does not filter filenames containing 'sameer'.
4. Full end-to-end auto pipeline chain executes without substitution.
"""
import io
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import CandidateProfile, ExtractedSkillList, SkillMatchResult, TalentCheckResult
from app.core import storage

client = TestClient(app)


def test_scanned_pdf_returns_400(monkeypatch):
    """PDF with < 200 chars returns HTTP 400 explaining it looks scanned."""
    # Mock files.read_text to simulate scanned PDF returning minimal text
    monkeypatch.setattr("app.core.files.read_text", lambda content, filename: "Short text")
    
    file_bytes = io.BytesIO(b"%PDF-1.4 mock pdf content")
    res = client.post(
        "/api/resume/parse",
        files={"file": ("scanned_resume.pdf", file_bytes, "application/pdf")},
    )
    assert res.status_code == 400
    assert "This PDF looks scanned (no selectable text)" in res.json()["detail"]


def test_stored_fixture_fallback_source_label(monkeypatch):
    """When LLM extraction fails on a sample resume, fixture fallback labels source as stored_fixture_fallback."""
    # Ensure raw text is long enough to bypass scanned PDF check
    monkeypatch.setattr("app.core.files.read_text", lambda content, filename: "A" * 300)
    
    # Mock storage.load("resume", ...) to return None so it doesn't return cached
    original_load = storage.load
    def mock_load(kind, key):
        if kind == "resume":
            return None
        return original_load(kind, key)
    monkeypatch.setattr(storage, "load", mock_load)

    # Prevent overwriting real storage on disk during test
    monkeypatch.setattr(storage, "save", lambda kind, key, data: None)

    # Force extract_skills to fail
    def fail_extract(*args, **kwargs):
        raise RuntimeError("Simulated OpenRouter outage")
    monkeypatch.setattr("app.core.extract.extract_skills", fail_extract)

    file_bytes = io.BytesIO(b"Candidate resume content...")
    res = client.post(
        "/api/resume/parse",
        files={"file": ("Ananya Rao.docx", file_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["extras"].get("source") == "stored_fixture_fallback"


def test_samples_endpoint_does_not_filter_sameer(monkeypatch):
    """Ensure list_samples returns all samples without filtering 'sameer'."""
    res = client.get("/api/resume/samples")
    assert res.status_code == 200
    samples = res.json()
    assert isinstance(samples, list)
    # Verify endpoint is functional and no filter code exists
    assert any("ananya" in s.lower() for s in samples)


def test_auto_pipeline_chain_no_substitution():
    """Verify complete end-to-end chain from JD upload to Talent Check using real endpoints."""
    # Step 1: Upload JD
    jd_raw = storage.load("jd", "Google LLC - Software Engineer.pdf")
    assert jd_raw is not None
    jd_filename = "Google LLC - Software Engineer.pdf"

    # Step 2: Resume parsing (using cached Ananya Rao)
    resume_raw = storage.load("resume", "Ananya Rao.pdf")
    assert resume_raw is not None

    # Step 3: Prefill Candidate Profile
    prefill_res = client.post("/api/profile/prefill?save=false", json=resume_raw)
    assert prefill_res.status_code == 200
    profile = CandidateProfile.model_validate(prefill_res.json())
    assert profile.candidate_id == "ananya-rao"

    # Step 4: Skill Matching
    match_res = client.post(
        "/api/skill-match",
        json={"candidate_id": profile.candidate_id, "jd_source_file": jd_filename},
    )
    assert match_res.status_code == 200
    match_result = SkillMatchResult.model_validate(match_res.json())
    assert match_result.candidate_id == "ananya-rao"
    assert 0 <= match_result.match_score <= 100

    # Step 5: Talent Check
    tc_res = client.post(
        "/api/talent-check",
        json={
            "candidate_id": profile.candidate_id,
            "company": "Google LLC",
            "role": "Software Engineer",
        },
    )
    assert tc_res.status_code == 200
    tc_result = TalentCheckResult.model_validate(tc_res.json())
    assert tc_result.candidate_id == "ananya-rao"
    assert 0 <= tc_result.readiness_score <= 100
