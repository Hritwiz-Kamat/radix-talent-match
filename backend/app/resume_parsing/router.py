"""
Resume Parsing API Router (Role 2).

Endpoints:
  GET  /api/resume/samples       -> List available sample resume files.
  POST /api/resume/parse         -> Parse uploaded resume file (multipart).
  POST /api/resume/parse-sample  -> Parse an existing sample resume by name.

Current state: returns mocks.MOCK_RESUME while wiring in file persistence and storage.
"""
from pathlib import Path
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app import mocks
from app.core import storage
from app.schemas import ExtractedSkillList

router = APIRouter(prefix="/api/resume", tags=["resume"])

# Directory where sample resumes are stored
RESUMES_DIR = Path(__file__).resolve().parents[2] / "data" / "resumes"


@router.get("/samples", response_model=list[str])
def list_samples() -> list[str]:
    """Return all sample resume filenames available in backend/data/resumes."""
    if not RESUMES_DIR.exists():
        return []
    # Ignore hidden files like .gitkeep
    return sorted(
        f.name for f in RESUMES_DIR.iterdir()
        if f.is_file() and not f.name.startswith(".")
    )


@router.post("/parse", response_model=ExtractedSkillList)
async def parse_resume(file: UploadFile = File(...)) -> ExtractedSkillList:
    """
    Upload and parse a candidate resume (PDF or DOCX).
    Currently returns MOCK_RESUME as a stub, saving file and result to storage.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload."
        )

    # Validate file extension
    ext = file.filename.lower().split(".")[-1]
    if ext not in ["pdf", "docx", "txt"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type .{ext}. Please upload a PDF or DOCX file."
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    # 1. Upload original file to candidate-files storage
    storage.upload_file(
        f"resume/{file.filename}",
        content,
        content_type=file.content_type or "application/octet-stream"
    )

    # 2. Return mock result configured with the uploaded filename (Step 1 of build order)
    result = mocks.MOCK_RESUME.model_copy(update={"source_file": file.filename})

    # 3. Save extracted result into documents table / local mirror (kind: "resume")
    storage.save("resume", file.filename, result)

    return result


@router.post("/parse-sample", response_model=ExtractedSkillList)
def parse_sample(name: str) -> ExtractedSkillList:
    """
    Parse an existing sample resume by filename.
    Currently returns MOCK_RESUME as a stub, saving result to storage.
    """
    sample_file = RESUMES_DIR / name
    if not sample_file.exists() or not sample_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample resume '{name}' not found."
        )

    # Return mock result configured with the sample filename
    result = mocks.MOCK_RESUME.model_copy(update={"source_file": name})

    # Save extracted result into storage (kind: "resume")
    storage.save("resume", name, result)

    return result
