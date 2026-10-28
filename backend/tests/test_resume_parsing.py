"""Unit and integration tests for Role 2 (Resume Parsing) endpoints."""
import io
from pathlib import Path
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


def test_parse_sample_flexible_lookup(client):
    """Resilience path: flexible lookup handles slug and case variations."""
    res = client.post("/api/resume/parse-sample?name=ananya-rao.docx")
    assert res.status_code == 200
    data = res.json()
    assert "Ananya Rao" in data["source_file"]


def test_parse_sample_not_found(client):
    """Bad-input path: missing sample returns 404 with helpful error message."""
    res = client.post("/api/resume/parse-sample?name=ghost_candidate_xyz.pdf")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_parse_upload_docx_success(client):
    """Happy path: uploading real DOCX resume extracts candidate information."""
    sample_docx = Path(__file__).resolve().parents[1] / "data" / "resumes" / "Ananya Rao.docx"
    assert sample_docx.exists(), "Sample Ananya Rao.docx must exist"
    with open(sample_docx, "rb") as f:
        files = {"file": ("Ananya Rao.docx", f.read(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    res = client.post("/api/resume/parse", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["source_file"] == "Ananya Rao.docx"
    assert len(data["skills"]) > 0


def test_parse_upload_empty_file(client):
    """Bad-input path: uploading empty file returns 400."""
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    res = client.post("/api/resume/parse", files=files)
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()


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
