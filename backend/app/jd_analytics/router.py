"""
JD Analytics API Router (Role 1).

Endpoints:
  GET  /api/jd-analytics/list     -> List all available analyzed and raw job descriptions.
  POST /api/jd-analytics/parse-jd -> Parse an existing JD from backend/data/jds/.
  POST /api/jd-analytics/upload   -> Upload and parse a custom JD (PDF, DOCX, TXT).
"""
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core import storage
from app.core.extract import extract_skills
from app.schemas import ExtractedSkillList

router = APIRouter(prefix="/api/jd-analytics", tags=["JD Analytics"])

JDS_DIR = Path(__file__).resolve().parents[2] / "data" / "jds"

JD_TASK_INSTRUCTIONS = (
    "Analyze this Job Description. Extract all technical and soft skills required "
    "by the employer. Pay special attention to determining whether the importance "
    "of each skill is 'required' or 'preferred'."
)


@router.get("/list")
def list_jds() -> list[dict]:
    """
    List all available job descriptions, combining stored extractions with local JD files.
    Powers the dynamic JD dropdown in JD Analytics and Skill Matching.
    """
    results_map: dict[str, dict] = {}

    # 1. Discover already-analyzed JDs from storage (kind='jd')
    for key in storage.list_keys("jd"):
        if key.startswith("_test_"):
            continue
        data = storage.load("jd", key)
        if data and isinstance(data, dict):
            # Strict classification: reject any document that is actually a resume
            if data.get("source_type") == "resume":
                continue
            extras = data.get("extras") or {}
            if extras.get("email") or extras.get("name"):
                continue
            src_file = data.get("source_file", key)
            if "resume" in src_file.lower() or "cv" in src_file.lower():
                continue

            company = data.get("company")
            role = data.get("role")
            skills = data.get("skills", [])
            title = f"{company} - {role}" if company and role else Path(src_file).stem
            canon = Path(src_file).stem.lower().replace(" ", "-").replace("_", "-")
            results_map[canon] = {
                "source_file": src_file,
                "title": title,
                "company": company,
                "role": role,
                "is_analyzed": True,
                "skills_count": len(skills),
            }

    # 2. Discover raw files in data/jds/ (deduplicate against already analyzed JDs)
    if JDS_DIR.exists():
        for f in JDS_DIR.iterdir():
            if f.is_file() and not f.name.startswith("."):
                canon = f.stem.lower().replace(" ", "-").replace("_", "-")
                if canon not in results_map:
                    stem = f.stem
                    parts = stem.split(" - ")
                    company = parts[0].strip() if len(parts) > 1 else None
                    role = parts[1].strip() if len(parts) > 1 else stem
                    results_map[canon] = {
                        "source_file": f.name,
                        "title": stem,
                        "company": company,
                        "role": role,
                        "is_analyzed": False,
                        "skills_count": 0,
                    }

    # Sort deterministically
    return sorted(results_map.values(), key=lambda x: x["title"])


@router.post("/parse-jd", response_model=ExtractedSkillList)
def parse_jd(filename: str = "sample_google_swe.pdf") -> ExtractedSkillList:
    """Extracts skills from a Job Description file using the shared extraction pipeline."""
    # Check if already analyzed in storage
    existing = storage.load("jd", filename)
    if existing and isinstance(existing, dict) and existing.get("skills"):
        try:
            return ExtractedSkillList.model_validate(existing)
        except Exception:
            pass

    file_path = JDS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Job description file not found: {filename}")

    from app.core import files
    content = file_path.read_bytes()
    try:
        raw_text = files.read_text(content, filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read text from JD file: {e}",
        )

    # Infer company and role from filename if possible
    stem = Path(filename).stem
    parts = stem.split(" - ")
    company = parts[0].strip() if len(parts) > 1 else None
    role = parts[1].strip() if len(parts) > 1 else stem

    result = extract_skills(
        text=raw_text,
        source_type="jd",
        source_file=filename,
        company=company,
        role=role,
        task_instructions=JD_TASK_INSTRUCTIONS,
    )
    storage.save("jd", filename, result)
    return result


@router.post("/upload", response_model=ExtractedSkillList)
async def upload_jd(file: UploadFile = File(...)) -> ExtractedSkillList:
    """Upload and analyze a custom Job Description (PDF, DOCX, TXT)."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload.",
        )

    ext = file.filename.lower().split(".")[-1]
    if ext not in ["pdf", "docx", "txt", "md"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type .{ext}. Please upload a PDF, DOCX, or TXT file.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # 1. Upload original file to candidate-files storage
    storage.upload_file(
        f"jd/{file.filename}",
        content,
        content_type=file.content_type or "application/octet-stream",
    )

    # 2. Extract text from JD bytes
    from app.core import files
    try:
        raw_text = files.read_text(content, file.filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read text from uploaded JD: {e}",
        )

    # Document classification check: verify this is a JD, not a candidate resume
    lower_text = raw_text.lower()
    lower_fn = file.filename.lower()
    is_resume_signal = (
        "resume" in lower_fn
        or "cv" in lower_fn
        or ("curriculum vitae" in lower_text)
        or ("education" in lower_text and "experience" in lower_text and any(k in lower_text for k in ["b.tech", "bachelor", "master", "gpa", "cgpa", "contact"]))
    )
    if is_resume_signal and not any(k in lower_text for k in ["job description", "responsibilities", "requirements", "about the role", "what you'll do", "we are looking"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file appears to be a candidate resume, not a Job Description. Please upload resumes in the Resume Parsing module.",
        )

    # 3. Infer company and role from filename or header
    stem = Path(file.filename).stem
    parts = stem.split(" - ")
    company = parts[0].strip() if len(parts) > 1 else None
    role = parts[1].strip() if len(parts) > 1 else stem

    # 4. Extract required and preferred skills
    result = extract_skills(
        text=raw_text,
        source_type="jd",
        source_file=file.filename,
        company=company,
        role=role,
        task_instructions=JD_TASK_INSTRUCTIONS,
    )

    # 5. Persist to storage
    storage.save("jd", file.filename, result)
    return result
