"""
Role 4 — Talent Check: pure scoring logic.

No LLM here — everything is deterministic arithmetic, so it's easy to test and explain.

Key idea:
  For each of the 12 skillsets, we compare how good the candidate is (candidate_level)
  against what the company expects (required_level).  The gap drives the readiness score.

How candidate_level is computed (from ROLE_4_TALENT_CHECK.md):
  • Find the strongest skill confidence in that category:
      high -> 7,  medium -> 5,  low -> 3
  • Add +1 for each *additional* skill in the same category (capped at +3 bonus).
  • Final value is capped at 10.  No skills in this category -> 0.

readiness_score formula (from ROLE_4_TALENT_CHECK.md):
  round(100 * sum(min(candidate, required)) / sum(required))   over the 12 skillsets.
  Exceeding the bar in one category does NOT compensate for a gap in another.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..schemas import (
    TWELVE_SKILLSETS,
    CandidateProfile,
    CategoryCode,
    Skill,
    SkillsetGap,
    TalentCheckResult,
)

# ---------------------------------------------------------------------------
# Confidence -> base numeric value
# ---------------------------------------------------------------------------
_CONF_SCORE: dict[str, int] = {"high": 7, "medium": 5, "low": 3}

# Path to the placeholder (and, eventually, the real) company skillsets file
_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_REAL_FILE = _DATA_DIR / "talent_check_company_skillsets.json"
_PLACEHOLDER = _DATA_DIR / "talent_check_company_skillsets.PLACEHOLDER.json"


# ---------------------------------------------------------------------------
# Company-levels loader — designed so swapping the real file is a 10-min job
# ---------------------------------------------------------------------------

def load_company_levels() -> list[dict]:
    """
    Load the list of company/role level dicts from storage first,
    falling back to the local JSON file.

    Returns a list like:
        [{"company": "Google LLC", "role": "Software Engineer",
          "levels": {"DSA": 9, "COD": 8, ...}}, ...]
    """
    # Try storage first (Supabase / local mirror seeded by seed_supabase.py)
    try:
        from ..core import storage  # imported here to keep scoring.py import-clean during unit tests
        raw = storage.load("company_skillsets", "all")
        if raw and "roles" in raw:
            return raw["roles"]
    except Exception:
        pass  # storage unavailable -> fall through to local file

    # Fall back to the local JSON file (real file preferred over placeholder)
    src = _REAL_FILE if _REAL_FILE.exists() else _PLACEHOLDER
    data = json.loads(src.read_text(encoding="utf-8"))
    return data["roles"]


def get_companies(levels: list[dict]) -> list[str]:
    """Return a sorted, deduplicated list of company names."""
    return sorted({r["company"] for r in levels})


def get_roles_for_company(company: str, levels: list[dict]) -> list[str]:
    """Return all role titles offered by a given company."""
    return [r["role"] for r in levels if r["company"] == company]


def find_level_entry(company: str, role: str, levels: list[dict]) -> dict[str, int] | None:
    """
    Look up the required levels dict for a specific company + role.
    Returns None if not found (caller should raise HTTP 404).
    """
    for entry in levels:
        if entry["company"] == company and entry["role"] == role:
            return entry["levels"]
    return None


# ---------------------------------------------------------------------------
# Candidate-level computation
# ---------------------------------------------------------------------------

def _candidate_level_for_category(skills: list[Skill], category: str) -> tuple[int, str]:
    """
    Given all of a candidate's skills, compute their 0-10 level for one category.

    Returns (level, explanation_string).

    Algorithm (from ROLE_4_TALENT_CHECK.md):
      1. Collect all skills whose category_code matches.
      2. If none -> (0, "no evidence").
      3. Find the highest-confidence one: high=7, medium=5, low=3.
      4. Add +1 per *additional* skill (max +3 bonus).
      5. Cap result at 10.
    """
    # Skills in this category only
    cat_skills = [s for s in skills if s.category_code == category]
    if not cat_skills:
        return 0, "no evidence"

    # Sort by confidence strength (high first)
    order = {"high": 0, "medium": 1, "low": 2}
    cat_skills.sort(key=lambda s: order[s.confidence])

    best = cat_skills[0]
    base = _CONF_SCORE[best.confidence]               # 7, 5, or 3
    bonus = min(len(cat_skills) - 1, 3)               # +1 per extra skill, cap 3
    level = min(base + bonus, 10)

    # Human-readable explanation for the UI ("why this score" panel)
    names = ", ".join(
        f"{s.skill_name}({s.confidence})" for s in cat_skills
    )
    explanation = (
        f"{len(cat_skills)} skill(s): {names} "
        f"-> base {base} + bonus {bonus} = {level}"
    )
    return level, explanation


# ---------------------------------------------------------------------------
# The main scoring function — pure, no side effects, easy to test
# ---------------------------------------------------------------------------

def score(
    profile: CandidateProfile,
    company_levels: dict[str, int],     # e.g. {"DSA": 9, "COD": 8, ...}
    company: str,
) -> TalentCheckResult:
    """
    Compare a CandidateProfile against one company/role's required levels.

    Pure function: same inputs always produce the same output.
    Uses only the 12 scored skillsets (OTHER is ignored, per the spec).

    readiness_score = round(100 * Σ min(cand, req) / Σ req)
      — exceeding the bar in one category can NOT hide a gap elsewhere.
    """
    gaps: list[SkillsetGap] = []
    sum_min = 0     # numerator:   sum of min(candidate, required)
    sum_req = 0     # denominator: sum of required levels

    for cat in TWELVE_SKILLSETS:
        required = company_levels.get(cat, 0)   # default 0 if company doesn't care
        candidate, explanation = _candidate_level_for_category(profile.skills, cat)

        gap_exists = candidate < required
        gap_size = max(0, required - candidate)

        gaps.append(SkillsetGap(
            category_code=cat,          # type: ignore[arg-type]
            required_level=required,
            candidate_level=candidate,
            gap=gap_exists,
            gap_size=gap_size,
            explanation=explanation,
        ))

        sum_min += min(candidate, required)
        sum_req += required

    # Avoid division-by-zero (extremely unlikely: no required levels set at all)
    readiness = round(100 * sum_min / sum_req) if sum_req > 0 else 0

    formula = (
        "readiness = round(100 × Σ min(candidate_level, required_level) / Σ required_level) "
        "over the 12 skillsets. "
        "candidate_level: strongest skill in category (high=7, med=5, low=3) "
        "+ 1 per additional skill in same category (max +3 bonus), capped at 10."
    )

    return TalentCheckResult(
        company=company,
        candidate_id=profile.candidate_id,
        skillset_gap=gaps,
        readiness_score=readiness,
        scoring_method=formula,
    )
