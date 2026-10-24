"""Unit and integration tests for Role 2 (Resume Parsing) endpoints."""
import io
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ExtractedSkillList


@pytest.fixture
def client():
    return TestClient(app)


def test_list_samples_returns_resumes(client):
    """Happy path: GET /api/resume/samples lists sample resumes."""
    res = client.get("/api/resume/samples")
    assert res.status_code == 200
    samples = res.json()
    assert isinstance(samples, list)
    assert len(samples) > 0
    assert any("Ananya Rao" in s for s in samples)


def test_parse_sample_happy_path(client):
    """Happy path: parse existing sample resume returns valid ExtractedSkillList."""
    res = client.post("/api/resume/parse-sample?name=Ananya Rao.pdf")
    assert res.status_code == 200
    data = res.json()
    validated = ExtractedSkillList(**data)
    assert validated.source_type == "resume"
    assert validated.source_file == "Ananya Rao.pdf"
    assert len(validated.skills) > 0


def test_parse_sample_not_found(client):
    """Bad-input path: missing sample returns 404 with helpful error message."""
    res = client.post("/api/resume/parse-sample?name=ghost_candidate.pdf")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_parse_upload_bad_extension(client):
    """Bad-input path: uploading invalid file type returns 400."""
    file_bytes = io.BytesIO(b"fake image data")
    files = {"file": ("resume.png", file_bytes, "image/png")}
    res = client.post("/api/resume/parse", files=files)
    assert res.status_code == 400
    assert "unsupported file type" in res.json()["detail"].lower()


def test_different_inputs_give_different_outputs(client):
    """Different inputs produce corresponding source_file outputs."""
    res1 = client.post("/api/resume/parse-sample?name=Ananya Rao.pdf")
    res2 = client.post("/api/resume/parse-sample?name=Karthik Subramaniam.pdf")

    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json()["source_file"] != res2.json()["source_file"]
    assert res1.json()["source_file"] == "Ananya Rao.pdf"
    assert res2.json()["source_file"] == "Karthik Subramaniam.pdf"
