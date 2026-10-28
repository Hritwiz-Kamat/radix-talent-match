"""
Profile Builder API Router (Role 3).

Endpoints:
  GET  /api/profile               -> List all saved candidate profiles.
  POST /api/profile               -> Create and persist a new candidate profile.
  GET  /api/profile/{candidate_id} -> Load one candidate profile.
  PUT  /api/profile/{candidate_id} -> Validate and update a candidate profile.
  POST /api/profile/prefill       -> Create profile draft from extracted resume (with auto_save).
  POST /api/profile/{candidate_id}/cv -> Upload CV and attach to candidate profile.
"""
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core import storage
from app.schemas import CandidateProfile, ExtractedSkillList

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _make_slug(name: str, fallback: str = "candidate") -> str:
    """Generate a clean URL-safe slug."""
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or fallback


@router.get("")
def list_profiles() -> list[dict[str, str]]:
    """List saved candidate profiles."""
    profiles = []

    for candidate_id in storage.list_keys("profiles"):
        if candidate_id.startswith("_test_"):
            continue
        data = storage.load("profiles", candidate_id)
        if data is not None and isinstance(data, dict):
            cid = data.get("candidate_id", candidate_id)
            profiles.append({
                "candidate_id": cid,
                "id": cid,  # full compatibility with TalentCheck and SkillMatching
                "name": data.get("name", candidate_id),
            })

    FIXTURE_IDS = {"ananya-rao", "karthik-subramaniam", "priya-menon", "rohan-verma"}
    # User-created profiles appear first, then alphabetically
    profiles.sort(key=lambda p: (p["candidate_id"] in FIXTURE_IDS, p["name"]))
    return profiles


@router.delete("/{candidate_id}")
def delete_profile(candidate_id: str):
    """Delete a candidate profile from storage."""
    cid = _make_slug(candidate_id)
    p = storage.ROOT / "profiles" / f"{cid}.json"
    if p.exists():
        p.unlink()
    if storage.supabase_enabled():
        try:
            with storage._client() as c:
                c.delete(f"{storage._url()}/rest/v1/{storage.TABLE}", params={"kind": f"eq.profiles", "key": f"eq.{cid}"})
        except Exception:
            pass
    return {"ok": True, "deleted": cid}


@router.post("", response_model=CandidateProfile, status_code=status.HTTP_201_CREATED)
def create_profile(profile: CandidateProfile) -> CandidateProfile:
    """Validate, create, and persist a new candidate profile."""
    # Ensure slug ID is clean
    cid = profile.candidate_id.strip() if profile.candidate_id else ""
    if not cid or cid == "new-candidate":
        cid = _make_slug(profile.name or "candidate")

    # If ID conflicts with a different person's profile, append a suffix
    existing = storage.load("profiles", cid)
    if existing and isinstance(existing, dict):
        existing_name = existing.get("name", "").strip().lower()
        new_name = profile.name.strip().lower()
        if existing_name and new_name and existing_name != new_name:
            import time
            cid = f"{cid}-{int(time.time()) % 10000}"

    persisted = profile.model_copy(update={"candidate_id": cid})
    storage.save("profiles", cid, persisted)
    return persisted


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
    """Validate and update an existing candidate profile."""
    if candidate_id != profile.candidate_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL candidate_id must match profile candidate_id.",
        )

    storage.save("profiles", candidate_id, profile)
    return profile


@router.post("/prefill", response_model=CandidateProfile)
def prefill_profile(extracted: ExtractedSkillList, save: bool = True) -> CandidateProfile:
    """
    Create a structured candidate profile from extracted resume data.
    When save=True (default), automatically persists to storage so the candidate
    immediately becomes available in all dropdowns and downstream modules.
    """
    if extracted.source_type != "resume":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prefill requires extracted resume data.",
        )

    extras = extracted.extras or {}
    filename = Path(extracted.source_file).stem

    # Extract name: prioritize extras name -> filename
    raw_name = extras.get("name")
    if raw_name and raw_name.strip():
        name = raw_name.strip()
    else:
        # Clean up filename (e.g. Sameer_Singla_Resume -> Sameer Singla)
        clean_fn = re.sub(r"[\(\)\d_]+", " ", filename).strip()
        clean_fn = re.sub(r"\b(resume|cv|updated|final)\b", "", clean_fn, flags=re.IGNORECASE).strip()
        name = clean_fn.title() or filename.replace("_", " ").title()

    candidate_id = _make_slug(name, fallback=_make_slug(filename))

    prof = CandidateProfile(
        candidate_id=candidate_id,
        name=name,
        email=extras.get("email"),
        education=extras.get("education"),
        skills=extracted.skills,
        hackathons=extras.get("hackathons", []),
        internships=extras.get("experience", []),
        certifications=extras.get("certifications", []),
        preferred_roles=[extracted.role] if extracted.role else [],
        cv_file=f"resume/{extracted.source_file}",
    )

    if save:
        storage.save("profiles", candidate_id, prof)

    return prof


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
