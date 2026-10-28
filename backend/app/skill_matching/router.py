"""
Skill Matching API Router (Role 5).

Endpoints:
  POST /api/skill-match         -> Calculate match score, matched skills, and missing skills.
  GET  /api/skill-match/matrix  -> Return match matrix across candidates and JDs.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, ValidationError

from app import mocks
from app.core import storage
from app.schemas import CandidateProfile, ExtractedSkillList, SkillMatchResult
from app.skill_matching.matching import build_skill_match_result

log = logging.getLogger("skill_matching")

router = APIRouter(prefix="/api/skill-match", tags=["skill-matching"])


class SkillMatchRequest(BaseModel):
    candidate_id: str = Field(min_length=1, description="Candidate ID slug, e.g. 'ananya-rao'")
    jd_source_file: str = Field(min_length=1, description="Job description identifier or filename")
    mock: Optional[bool] = Field(default=False, description="Set True for offline demo or mock fallback")


class MatrixEntry(BaseModel):
    candidate_id: str
    jd_source_file: str
    match_score: int


class MatrixResponse(BaseModel):
    matrix: list[MatrixEntry]


@router.post("", response_model=SkillMatchResult)
def match_skills(req: SkillMatchRequest) -> SkillMatchResult:
    """
    Compare a candidate profile with an extracted job description.
    Loads candidate from storage (kind 'profiles') and JD from storage (kind 'jd').
    Executes the 4-tier matching engine, persists result in storage (kind 'results'),
    and returns the validated SkillMatchResult.
    """
    # Explicit mock fallback (useful for frontend testing before other roles finish)
    if req.mock:
        return mocks.MOCK_MATCH.model_copy(
            update={
                "candidate_id": req.candidate_id,
                "jd_source_file": req.jd_source_file,
            }
        )

    # 1. Load candidate profile from storage
    raw_cand = storage.load("profiles", req.candidate_id)
    if raw_cand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile '{req.candidate_id}' not found.",
        )
    try:
        candidate = CandidateProfile.model_validate(raw_cand)
    except ValidationError as e:
        log.error("Stored candidate profile for '%s' failed validation: %s", req.candidate_id, e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Stored candidate profile for '{req.candidate_id}' is invalid: {e.errors()}",
        )

    # 2. Load extracted JD skills from storage (with auto-extension fallback and on-the-fly parsing)
    raw_jd = storage.load('jd', req.jd_source_file)
    if raw_jd is None:
        alt_ext = None
        if req.jd_source_file.lower().endswith('.docx'):
            alt_ext = req.jd_source_file[:-5] + '.pdf'
        elif req.jd_source_file.lower().endswith('.pdf'):
            alt_ext = req.jd_source_file[:-4] + '.docx'

        if alt_ext:
            raw_jd = storage.load('jd', alt_ext)

        if raw_jd is None:
            try:
                from app.jd_analytics.router import parse_jd
                analyzed = parse_jd(filename=req.jd_source_file)
                raw_jd = analyzed.model_dump()
            except Exception:
                if alt_ext:
                    try:
                        from app.jd_analytics.router import parse_jd
                        analyzed = parse_jd(filename=alt_ext)
                        raw_jd = analyzed.model_dump()
                    except Exception:
                        pass

    if raw_jd is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Extracted job description '{req.jd_source_file}' not found in storage. Has Role 1 analysed this JD?",
        )
    try:
        jd = ExtractedSkillList.model_validate(raw_jd)
    except ValidationError as e:
        log.error("Stored job description for '%s' failed validation: %s", req.jd_source_file, e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Stored job description for '{req.jd_source_file}' is invalid: {e.errors()}",
        )

    # 3. Execute 4-tier matching pipeline
    result = build_skill_match_result(
        candidate_id=candidate.candidate_id,
        jd_source_file=req.jd_source_file,
        candidate_skills=candidate.skills,
        job_skills=jd.skills,
        use_llm=True,
        use_cache=True,
    )

    # 4. Save result to storage (kind: 'results')
    result_key = f"match-{candidate.candidate_id}-{req.jd_source_file}"
    try:
        storage.save("results", result_key, result)
    except Exception as e:
        log.warning("Storage save failed for result '%s': %s", result_key, e)

    return result


@router.get("/matrix", response_model=MatrixResponse)
def get_match_matrix() -> MatrixResponse:
    """
    Retrieve all saved match results across candidates and job descriptions.
    Builds the matrix dynamically from stored documents without recalculating.
    """
    keys = storage.list_keys("results")
    entries: list[MatrixEntry] = []

    for key in keys:
        if not key.startswith("match-"):
            continue
        try:
            doc = storage.load("results", key)
            if not doc or not isinstance(doc, dict):
                continue
            jd_src = str(doc.get("jd_source_file", ""))
            # Exclude mistaken results where a resume was matched as a JD or test keys
            if "resume" in jd_src.lower() or "cv" in jd_src.lower() or "_test_" in key:
                continue
            if "candidate_id" in doc and "jd_source_file" in doc and "match_score" in doc:
                entries.append(
                    MatrixEntry(
                        candidate_id=str(doc["candidate_id"]),
                        jd_source_file=str(doc["jd_source_file"]),
                        match_score=int(doc["match_score"]),
                    )
                )
        except Exception as e:
            log.warning("Skipping unreadable match result key '%s': %s", key, e)

    # Sort deterministically by candidate_id, then jd_source_file
    entries.sort(key=lambda x: (x.candidate_id, x.jd_source_file))
    return MatrixResponse(matrix=entries)
