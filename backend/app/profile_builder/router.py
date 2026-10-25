
"""Profile Builder API Router (Role 3)."""

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app import mocks
from app.core import storage
from app.schemas import CandidateProfile, ExtractedSkillList

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("")
def list_profiles() -> list[dict[str, str]]:
    """List saved candidate profiles."""
    profiles = []

    for candidate_id in storage.list_keys("profiles"):
        data = storage.load("profiles", candidate_id)
        if data is not None:
            profiles.append({
                "candidate_id": data["candidate_id"],
                "name": data.get("name", candidate_id),
            })

    return profiles


@router.get("/{candidate_id}", response_model=CandidateProfile)
def get_profile(candidate_id: str) -> CandidateProfile:
    """Load one candidate profile."""
    data = storage.load("profiles", candidate_id)

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{candidate_id}' not found.",
        )

    return CandidateProfile.model_validate(data)


@router.put("/{candidate_id}", response_model=CandidateProfile)
def save_profile(
    candidate_id: str, profile: CandidateProfile
) -> CandidateProfile:
    """Validate and save a candidate profile."""
    if candidate_id != profile.candidate_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL candidate_id must match profile candidate_id.",
        )

    storage.save("profiles", candidate_id, profile)
    return profile


@router.post("/prefill", response_model=CandidateProfile)
def prefill_profile(extracted: ExtractedSkillList) -> CandidateProfile:
    """Create an unsaved profile draft from extracted resume data."""
    if extracted.source_type != "resume":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prefill requires extracted resume data.",
        )

    extras = extracted.extras
    filename = Path(extracted.source_file).stem
    candidate_id = filename.lower().replace("_", "-").replace(" ", "-")

    name = extras.get("name") or filename.replace("_", " ").title()

    return CandidateProfile(
        candidate_id=candidate_id or "new-candidate",
        name=name,
        email=extras.get("email"),
        education=extras.get("education"),
        skills=extracted.skills,
        hackathons=extras.get("hackathons", []),
        internships=extras.get("experience", []),
        certifications=extras.get("certifications", []),
        preferred_roles=[extracted.role] if extracted.role else [],
    )


@router.post("/{candidate_id}/cv", response_model=CandidateProfile)
async def upload_cv(
    candidate_id: str, file: UploadFile = File(...)
) -> CandidateProfile:
    """Upload a CV and attach its stored path to the candidate profile."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided.",
        )

    filename = Path(file.filename).name
    extension = Path(filename).suffix.lower()

    if extension not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Upload a PDF, DOCX, or TXT file.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    data = storage.load("profiles", candidate_id)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{candidate_id}' not found.",
        )

    profile = CandidateProfile.model_validate(data)
    stored_path = storage.upload_file(
        f"cv/{candidate_id}/{filename}",
        content,
        content_type=file.content_type or "application/octet-stream",
    )

    updated_profile = profile.model_copy(update={"cv_file": stored_path})
    storage.save("profiles", candidate_id, updated_profile)
    return updated_profile
