"""
Role 4 — Talent Check API Router.

Endpoints (prefix /api/talent-check):
  GET  /api/talent-check/companies
      -> {"companies": [...], "roles_by_company": {...}}
      List every company and its available roles from the loaded skillsets data.

  POST /api/talent-check
      body: {"candidate_id": "ananya-rao", "company": "Google LLC", "role": "Software Engineer"}
      -> TalentCheckResult
      Loads the CandidateProfile from storage, runs the scoring function, saves and returns the result.

  GET  /api/talent-check/compare?company=...&role=...
      -> list[TalentCheckResult]
      Scores ALL saved candidate profiles against one company+role.
      Powers the multi-candidate comparison bar chart in the UI.
"""

import re

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core import storage
from app.schemas import CandidateProfile, TalentCheckResult
from app.talent_check.scoring import (
    find_level_entry,
    find_full_entry,
    get_companies,
    get_roles_for_company,
    load_company_levels_with_source,
    score,
)

router = APIRouter(prefix="/api/talent-check", tags=["talent-check"])


# ---------------------------------------------------------------------------
# Helper: load company levels once per request (cheap — reads local JSON/storage)
# ---------------------------------------------------------------------------
def _levels():
    return load_company_levels_with_source()


# ---------------------------------------------------------------------------
# GET /api/talent-check/companies
# ---------------------------------------------------------------------------
@router.get("/companies")
def list_companies():
    """
    Return all companies and their available roles.
    The frontend uses this to populate the company picker + role dropdown.
    """
    levels, data_source = _levels()
    companies = get_companies(levels)
    roles_by_company = {c: get_roles_for_company(c, levels) for c in companies}
    return {"companies": companies, "roles_by_company": roles_by_company}


# ---------------------------------------------------------------------------
# GET /api/talent-check/candidates
# ---------------------------------------------------------------------------
@router.get("/candidates")
def list_candidates():
    """
    Return all saved candidate profiles as [{id, name}].

    Reads storage.list_keys('profiles') and loads the 'name' field from each.
    The frontend uses this to populate its candidate picker dynamically,
    so new profiles added by Role 3 appear without any frontend code change.

    Keys beginning with '_test_' are silently excluded — they are only ever
    written by test/verification scripts and must never reach the UI dropdown.

    No new Pydantic model needed — the response is a plain list of dicts.
    """
    keys = storage.list_keys("profiles")
    result = []
    for key in keys:
        # Skip internal test profiles injected by scripts (e.g. _test_no_name_profile).
        # Real profiles written by Role 3 (Profile Builder) never use this prefix.
        if key.startswith("_test_"):
            continue
        raw = storage.load("profiles", key)
        if raw and isinstance(raw, dict):
            result.append({
                "id":   raw.get("candidate_id", key),   # slug, e.g. "ananya-rao"
                "name": raw.get("name", key),            # display name, e.g. "Ananya Rao"
            })
    return result





# ---------------------------------------------------------------------------
# POST /api/talent-check
# ---------------------------------------------------------------------------
class TalentCheckRequest(BaseModel):
    candidate_id: str
    company: str
    role: str


@router.post("", response_model=TalentCheckResult)
def run_talent_check(req: TalentCheckRequest) -> TalentCheckResult:
    """
    Score one candidate against one company role.

    1. Load the CandidateProfile from storage (kind='profiles', key=candidate_id).
    2. Look up the required skill levels for the requested company + role.
    3. Run the pure score() function.
    4. Persist the result to storage (kind='results', key=candidate_id+company+role).
    5. Return the TalentCheckResult.
    """
    # --- 1. Load candidate profile ---
    raw_profile = storage.load("profiles", req.candidate_id)
    if raw_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate '{req.candidate_id}' not found in storage. "
                   f"Available IDs: {storage.list_keys('profiles')}",
        )
    try:
        profile = CandidateProfile(**raw_profile)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Stored profile is malformed: {e}",
        )

    # --- 2. Look up company/role levels (full entry for aggregate + weights) ---
    levels, data_source = _levels()
    entry = find_full_entry(req.company, req.role, levels)
    if entry is None:
        available = [
            f"{r['company']} / {r['role']}" for r in levels
        ]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company '{req.company}' / role '{req.role}' not found. "
                   f"Available: {available}",
        )

    # --- 3. Score (pass aggregate + weights so UI can show provenance) ---
    result = score(
        profile,
        entry["levels"],
        req.company,
        company_aggregates=entry.get("aggregate"),
        role_weights_used=entry.get("weights_used"),
        data_source=data_source,
    )

    # --- 4. Persist result ---
    # Key: slugified candidate + company + role for uniqueness
    result_key = re.sub(r"[^a-z0-9]+", "-", f"{req.candidate_id}-{req.company}-{req.role}".lower()).strip("-")
    storage.save("results", result_key, result)

    return result


# ---------------------------------------------------------------------------
# GET /api/talent-check/compare
# ---------------------------------------------------------------------------
@router.get("/compare", response_model=list[TalentCheckResult])
def compare_candidates(company: str, role: str) -> list[TalentCheckResult]:
    """
    Score ALL saved candidate profiles against one company + role.
    Returns a list sorted by readiness_score descending.
    Powers the multi-candidate comparison bar chart on the frontend.
    """
    levels, data_source = _levels()
    entry = find_full_entry(company, role, levels)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company '{company}' / role '{role}' not found.",
        )

    candidate_keys = storage.list_keys("profiles")
    if not candidate_keys:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No candidate profiles found in storage.",
        )

    results: list[TalentCheckResult] = []
    for key in candidate_keys:
        raw = storage.load("profiles", key)
        if raw is None:
            continue
        try:
            profile = CandidateProfile(**raw)
        except Exception:
            continue   # skip malformed profiles silently, don't crash the whole compare
        results.append(score(
            profile,
            entry["levels"],
            company,
            company_aggregates=entry.get("aggregate"),
            role_weights_used=entry.get("weights_used"),
            data_source=data_source,
        ))

    results.sort(key=lambda r: r.readiness_score, reverse=True)
    return results
