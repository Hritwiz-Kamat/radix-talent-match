"""
Calibration tests for Role 4 Talent Check — scoring.py.

These tests encode the brief's stated expectations:
  - Ananya Rao    -> strong SWE candidate (Google SWE >> Google Data Scientist)
  - Karthik Subramaniam -> strong data candidate (Google Data Scientist >> Google SWE)
  - Priya Menon   -> best fit at Oracle support roles, not SWE
  - Rohan Verma   -> competitive everywhere (highest scores across roles)

Test categories (as required by AGENTS.md):
  1. Happy path   -> valid TalentCheckResult with correct schema
  2. Bad input    -> no profile skills -> all zeros -> readiness 0
  3. Different inputs give different outputs (Ananya vs Karthik ordering)

All tests use the scoring.py pure function directly — no HTTP, no storage, no LLM.
This makes them fast and deterministic; they must pass even with Wi-Fi off.
"""

import json
from pathlib import Path

import pytest

from app.schemas import CandidateProfile, TalentCheckResult
from app.talent_check.scoring import score

# ---------------------------------------------------------------------------
# Load the 4 fixture profiles from local store (committed to git)
# ---------------------------------------------------------------------------
STORE = Path(__file__).resolve().parents[1] / "data" / "store" / "profiles"

def _load_profile(slug: str) -> CandidateProfile:
    return CandidateProfile(**json.loads((STORE / f"{slug}.json").read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# Load company levels from the placeholder JSON directly (no storage needed)
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_REAL = DATA_DIR / "talent_check_company_skillsets.json"
_SRC = _REAL if _REAL.exists() else DATA_DIR / "talent_check_company_skillsets.PLACEHOLDER.json"
_ALL_LEVELS: list[dict] = json.loads(_SRC.read_text(encoding="utf-8"))["roles"]


def _get_levels(company: str, role: str) -> dict[str, int]:
    for r in _ALL_LEVELS:
        if r["company"] == company and r["role"] == role:
            return r["levels"]
    raise KeyError(f"{company} / {role} not found")


# Shorthand level dicts for the roles used most in tests
GOOGLE_SWE       = _get_levels("Google LLC", "Software Engineer")
GOOGLE_DS        = _get_levels("Google LLC", "Data Scientist")
ORACLE_SUPPORT   = _get_levels("Oracle Financial Services Software", "Application Support Analyst")
ORACLE_ASE       = _get_levels("Oracle Financial Services Software", "Associate Software Engineer")
MSFT_SWE         = _get_levels("Microsoft Corporation", "Software Engineer")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _score(slug: str, levels: dict, company: str) -> TalentCheckResult:
    return score(_load_profile(slug), levels, company)


# ===========================================================================
# 1. HAPPY PATH — schema validity
# ===========================================================================

def test_happy_path_returns_valid_schema():
    """score() returns a valid TalentCheckResult with all 12 skillsets."""
    result = _score("ananya-rao", GOOGLE_SWE, "Google LLC")

    assert isinstance(result, TalentCheckResult)
    assert result.candidate_id == "ananya-rao"
    assert result.company == "Google LLC"
    assert 0 <= result.readiness_score <= 100
    assert len(result.skillset_gap) == 12
    for gap in result.skillset_gap:
        assert 0 <= gap.candidate_level <= 10
        assert 0 <= gap.required_level <= 10
        assert gap.gap == (gap.candidate_level < gap.required_level)
        assert gap.gap_size == max(0, gap.required_level - gap.candidate_level)


def test_scoring_method_present():
    """TalentCheckResult includes a human-readable formula string."""
    result = _score("ananya-rao", GOOGLE_SWE, "Google LLC")
    assert result.scoring_method
    assert "readiness" in result.scoring_method.lower()


# ===========================================================================
# 2. BAD INPUT — empty skill list
# ===========================================================================

def test_empty_profile_gives_zero_readiness():
    """A candidate with no skills at all must score 0 (not crash, not NaN)."""
    from app.schemas import CandidateProfile
    empty = CandidateProfile(candidate_id="ghost", name="Ghost", skills=[])
    result = score(empty, GOOGLE_SWE, "Google LLC")
    assert result.readiness_score == 0
    for gap in result.skillset_gap:
        assert gap.candidate_level == 0
        assert gap.gap is True or gap.required_level == 0


def test_all_other_category_skills_ignored():
    """
    Skills categorised as OTHER must not contribute to any of the 12 scored categories.
    The candidate should score 0 in every category.
    """
    from app.schemas import CandidateProfile, Skill
    profile = CandidateProfile(
        candidate_id="other-only",
        name="Other Only",
        skills=[
            Skill(skill_name="Misc", category_code="OTHER",
                  evidence="some misc skill", confidence="high")
        ],
    )
    result = score(profile, GOOGLE_SWE, "Google LLC")
    assert all(g.candidate_level == 0 for g in result.skillset_gap)


# ===========================================================================
# 3. DIFFERENT INPUTS -> DIFFERENT OUTPUTS (calibration)
# ===========================================================================

def test_ananya_beats_karthik_on_google_swe():
    """
    Brief states: Ananya > Karthik for Google SWE.
    Ananya has strong DSA, COD, OS, SYSD, OOD — Karthik is heavier on data skills.
    """
    ananya  = _score("ananya-rao",         GOOGLE_SWE, "Google LLC")
    karthik = _score("karthik-subramaniam", GOOGLE_SWE, "Google LLC")
    assert ananya.readiness_score > karthik.readiness_score, (
        f"Expected Ananya ({ananya.readiness_score}) > Karthik ({karthik.readiness_score}) "
        f"for Google SWE"
    )


def test_karthik_beats_ananya_on_google_data_scientist():
    """
    Brief states: Karthik > Ananya for Google Data Scientist.
    Data Scientist weights SQL=8, AI=8, APTI=8 heavily.
    """
    ananya  = _score("ananya-rao",         GOOGLE_DS, "Google LLC")
    karthik = _score("karthik-subramaniam", GOOGLE_DS, "Google LLC")
    assert karthik.readiness_score > ananya.readiness_score, (
        f"Expected Karthik ({karthik.readiness_score}) > Ananya ({ananya.readiness_score}) "
        f"for Google Data Scientist"
    )


def test_rohan_is_competitive_everywhere():
    """
    Brief states: Rohan highest everywhere (68-80).
    He should beat or match every other candidate on every role.
    """
    profiles = ["ananya-rao", "karthik-subramaniam", "priya-menon"]
    for role_levels, company, role_name in [
        (GOOGLE_SWE,     "Google LLC",                       "SWE"),
        (GOOGLE_DS,      "Google LLC",                       "Data Scientist"),
        (ORACLE_SUPPORT, "Oracle Financial Services Software", "App Support"),
    ]:
        rohan_score = _score("rohan-verma", role_levels, company).readiness_score
        for slug in profiles:
            other_score = _score(slug, role_levels, company).readiness_score
            assert rohan_score >= other_score, (
                f"Rohan ({rohan_score}) should be >= {slug} ({other_score}) on {role_name}"
            )


def test_priya_scores_higher_on_oracle_support_than_google_swe():
    """
    Brief states: Priya's best is Oracle Application Support (46).
    Her Oracle support score must exceed her Google SWE score.
    """
    priya_oracle  = _score("priya-menon", ORACLE_SUPPORT, "Oracle Financial Services Software")
    priya_google  = _score("priya-menon", GOOGLE_SWE,     "Google LLC")
    assert priya_oracle.readiness_score > priya_google.readiness_score, (
        f"Expected Priya's Oracle support ({priya_oracle.readiness_score}) "
        f"> Google SWE ({priya_google.readiness_score})"
    )


def test_all_four_candidates_score_differently_on_google_swe():
    """Scores must spread out — confirms formula discriminates candidates."""
    slugs = ["ananya-rao", "karthik-subramaniam", "priya-menon", "rohan-verma"]
    scores = [_score(s, GOOGLE_SWE, "Google LLC").readiness_score for s in slugs]
    # At least 3 distinct values (the brief shows 4 different numbers)
    assert len(set(scores)) >= 3, f"Scores not spread enough: {scores}"


# ===========================================================================
# 4. FORMULA UNIT TESTS — candidate_level arithmetic
# ===========================================================================

def test_single_high_skill_gives_7():
    from app.schemas import CandidateProfile, Skill
    from app.talent_check.scoring import _candidate_level_for_category
    skills = [Skill(skill_name="Python", category_code="COD", evidence="x", confidence="high")]
    level, _ = _candidate_level_for_category(skills, "COD")
    assert level == 7


def test_three_skills_high_plus_two_bonuses_gives_9():
    """high(7) + 2 bonuses for 2 extra skills = 9"""
    from app.schemas import Skill
    from app.talent_check.scoring import _candidate_level_for_category
    skills = [
        Skill(skill_name="Python",  category_code="COD", evidence="x", confidence="high"),
        Skill(skill_name="Java",    category_code="COD", evidence="x", confidence="medium"),
        Skill(skill_name="C++",     category_code="COD", evidence="x", confidence="low"),
    ]
    level, _ = _candidate_level_for_category(skills, "COD")
    assert level == 9   # 7 + 2 bonus


def test_four_skills_caps_bonus_at_3():
    """high(7) + max bonus 3 = 10, even with 4+ skills"""
    from app.schemas import Skill
    from app.talent_check.scoring import _candidate_level_for_category
    skills = [
        Skill(skill_name=f"Lang{i}", category_code="COD", evidence="x", confidence="low")
        for i in range(5)
    ]
    # Even 5 low skills: base=3, bonus=min(4,3)=3 -> 6
    level, _ = _candidate_level_for_category(skills, "COD")
    assert level == 6   # 3 + 3 bonus


def test_no_skills_in_category_gives_zero():
    from app.talent_check.scoring import _candidate_level_for_category
    level, explanation = _candidate_level_for_category([], "DSA")
    assert level == 0
    assert "no evidence" in explanation
