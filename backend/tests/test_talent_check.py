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
# Load company levels — mirrors the same priority order as load_company_levels()
# but without touching storage (tests must be offline-safe).
# ---------------------------------------------------------------------------
DATA_DIR  = Path(__file__).resolve().parents[1] / "data"
_REAL     = DATA_DIR / "talent_check_company_skillsets.json"
_CSV      = Path(__file__).resolve().parents[1] / "app" / "talent_check" / "staging_company_skill_levels_rows.csv"
_PLACEHOLDER_FILE = DATA_DIR / "talent_check_company_skillsets.PLACEHOLDER.json"


def _load_all_levels() -> list[dict]:
    """Load company levels using the same priority chain as scoring.load_company_levels()."""
    # 1. Real JSON file (if manually placed)
    if _REAL.exists():
        return json.loads(_REAL.read_text(encoding="utf-8"))["roles"]
    # 2. CSV snapshot (primary local source)
    if _CSV.exists():
        from app.talent_check.scoring import load_company_levels_from_csv
        return load_company_levels_from_csv()
    # 3. Placeholder
    return json.loads(_PLACEHOLDER_FILE.read_text(encoding="utf-8"))["roles"]


_ALL_LEVELS: list[dict] = _load_all_levels()


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


# ---------------------------------------------------------------------------
# Endpoint tests: GET /api/talent-check/candidates
# Tests that _test_ prefixed profiles are excluded from the dropdown,
# and that all four real candidates are present with correct id/name shape.
# Uses FastAPI TestClient + unittest.mock to avoid Supabase calls.
# ---------------------------------------------------------------------------

def test_candidates_endpoint_excludes_test_prefix_profiles():
    """
    _test_no_name_profile (or any _test_* key) must never appear in /candidates.

    Root cause context: storage.save() writes to both local disk AND Supabase.
    If a test script saves a _test_ key, only the local file is easy to clean up.
    The Supabase row persists and is returned by list_keys().
    The endpoint filters them at the key level — before any load() call.
    """
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from app.main import app

    # Simulate storage returning the rogue key alongside real ones
    fake_keys = [
        "_test_no_name_profile",
        "ananya-rao",
        "karthik-subramaniam",
        "priya-menon",
        "rohan-verma",
    ]
    fake_profiles = {
        "_test_no_name_profile": {"candidate_id": "_test_no_name_profile", "skills": []},
        "ananya-rao":            {"candidate_id": "ananya-rao",            "name": "Ananya Rao",            "skills": []},
        "karthik-subramaniam":   {"candidate_id": "karthik-subramaniam",   "name": "Karthik Subramaniam",   "skills": []},
        "priya-menon":           {"candidate_id": "priya-menon",           "name": "Priya Menon",           "skills": []},
        "rohan-verma":           {"candidate_id": "rohan-verma",           "name": "Rohan Verma",           "skills": []},
    }

    with patch("app.talent_check.router.storage.list_keys", return_value=fake_keys), \
         patch("app.talent_check.router.storage.load", side_effect=lambda kind, key: fake_profiles.get(key)):
        client = TestClient(app)
        r = client.get("/api/talent-check/candidates")

    assert r.status_code == 200
    ids = [c["id"] for c in r.json()]
    assert "_test_no_name_profile" not in ids, (
        "_test_no_name_profile must be excluded from /candidates"
    )


def test_candidates_endpoint_returns_all_four_real_candidates():
    """All four real candidates must appear in /candidates with correct id and name."""
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from app.main import app

    real_keys = ["ananya-rao", "karthik-subramaniam", "priya-menon", "rohan-verma"]
    real_profiles = {
        "ananya-rao":          {"candidate_id": "ananya-rao",          "name": "Ananya Rao",          "skills": []},
        "karthik-subramaniam": {"candidate_id": "karthik-subramaniam", "name": "Karthik Subramaniam", "skills": []},
        "priya-menon":         {"candidate_id": "priya-menon",         "name": "Priya Menon",         "skills": []},
        "rohan-verma":         {"candidate_id": "rohan-verma",         "name": "Rohan Verma",         "skills": []},
    }

    with patch("app.talent_check.router.storage.list_keys", return_value=real_keys), \
         patch("app.talent_check.router.storage.load", side_effect=lambda kind, key: real_profiles.get(key)):
        client = TestClient(app)
        r = client.get("/api/talent-check/candidates")

    assert r.status_code == 200
    candidates = r.json()
    ids = [c["id"] for c in candidates]
    assert "ananya-rao"          in ids
    assert "karthik-subramaniam" in ids
    assert "priya-menon"         in ids
    assert "rohan-verma"         in ids
    assert len(candidates) == 4


def test_candidates_endpoint_response_shape():
    """Each entry in /candidates must have 'id' and 'name' fields and both must be non-empty."""
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from app.main import app

    keys = ["ananya-rao", "rohan-verma"]
    profiles = {
        "ananya-rao":  {"candidate_id": "ananya-rao",  "name": "Ananya Rao",  "skills": []},
        "rohan-verma": {"candidate_id": "rohan-verma", "name": "Rohan Verma", "skills": []},
    }

    with patch("app.talent_check.router.storage.list_keys", return_value=keys), \
         patch("app.talent_check.router.storage.load", side_effect=lambda kind, key: profiles.get(key)):
        client = TestClient(app)
        r = client.get("/api/talent-check/candidates")

    assert r.status_code == 200
    for entry in r.json():
        assert "id" in entry,   f"missing 'id' in {entry}"
        assert "name" in entry, f"missing 'name' in {entry}"
        assert entry["id"],     f"'id' is empty in {entry}"
        assert entry["name"],   f"'name' is empty in {entry}"


# ===========================================================================
# 5. CSV LOADER TESTS  (new — verifies the staging_company_skill_levels_rows.csv
#    integration added in this sprint)
# ===========================================================================

def test_parse_level_extracts_integer():
    """_parse_level must strip the company-acronym suffix and return the int."""
    from app.talent_check.scoring import _parse_level
    assert _parse_level("5-AP")   == 5
    assert _parse_level("9 - EV") == 9
    assert _parse_level("10-CR")  == 10
    assert _parse_level("7 - AS") == 7
    assert _parse_level("")       == 0    # blank -> 0


def test_csv_loader_returns_entries():
    """load_company_levels_from_csv() must return a non-empty list of dicts."""
    from app.talent_check.scoring import load_company_levels_from_csv
    entries = load_company_levels_from_csv()
    assert isinstance(entries, list)
    assert len(entries) > 0, "CSV loader returned no entries"
    # Every entry must have the required keys
    for e in entries:
        assert "company" in e
        assert "role"    in e
        assert "levels"  in e
        assert isinstance(e["levels"], dict)


def test_csv_loader_three_in_scope_companies_present():
    """The three in-scope companies must appear with their correct canonical names."""
    from app.talent_check.scoring import load_company_levels_from_csv
    entries = load_company_levels_from_csv()
    companies = {e["company"] for e in entries}
    assert "Google LLC"                         in companies
    assert "Microsoft Corporation"              in companies
    assert "Oracle Financial Services Software" in companies


def test_csv_loader_google_has_two_roles():
    """Google LLC must have exactly Software Engineer and Data Scientist entries."""
    from app.talent_check.scoring import load_company_levels_from_csv
    entries = load_company_levels_from_csv()
    google_roles = sorted(e["role"] for e in entries if e["company"] == "Google LLC")
    assert "Software Engineer" in google_roles
    assert "Data Scientist"    in google_roles


def test_csv_loader_oracle_has_two_roles():
    """Oracle Financial Services Software must have ASE and Application Support Analyst."""
    from app.talent_check.scoring import load_company_levels_from_csv
    entries = load_company_levels_from_csv()
    oracle_roles = sorted(
        e["role"] for e in entries
        if e["company"] == "Oracle Financial Services Software"
    )
    assert "Associate Software Engineer"   in oracle_roles
    assert "Application Support Analyst"   in oracle_roles


def test_csv_loader_levels_are_valid_ints():
    """Every level value in every entry must be an int in [0, 10]."""
    from app.talent_check.scoring import load_company_levels_from_csv
    from app.schemas import TWELVE_SKILLSETS
    entries = load_company_levels_from_csv()
    for e in entries:
        for code in TWELVE_SKILLSETS:
            val = e["levels"].get(code)
            assert isinstance(val, int), (
                f"{e['company']} / {e['role']} / {code}: expected int, got {val!r}"
            )
            assert 0 <= val <= 10, (
                f"{e['company']} / {e['role']} / {code}: {val} out of range [0, 10]"
            )


def test_csv_based_calibration_ananya_beats_karthik_swe():
    """With CSV-derived levels, Ananya still outscores Karthik on Google SWE."""
    from app.talent_check.scoring import load_company_levels_from_csv, find_level_entry
    levels = load_company_levels_from_csv()
    g_swe = find_level_entry("Google LLC", "Software Engineer", levels)
    assert g_swe is not None, "Google LLC / Software Engineer not found in CSV levels"
    ananya  = _score("ananya-rao",         g_swe, "Google LLC")
    karthik = _score("karthik-subramaniam", g_swe, "Google LLC")
    assert ananya.readiness_score > karthik.readiness_score, (
        f"CSV calibration: Ananya ({ananya.readiness_score}) must > Karthik ({karthik.readiness_score}) on Google SWE"
    )


def test_csv_based_calibration_karthik_beats_ananya_ds():
    """With CSV-derived levels, Karthik still outscores Ananya on Google Data Scientist."""
    from app.talent_check.scoring import load_company_levels_from_csv, find_level_entry
    levels = load_company_levels_from_csv()
    g_ds = find_level_entry("Google LLC", "Data Scientist", levels)
    assert g_ds is not None, "Google LLC / Data Scientist not found in CSV levels"
    ananya  = _score("ananya-rao",         g_ds, "Google LLC")
    karthik = _score("karthik-subramaniam", g_ds, "Google LLC")
    assert karthik.readiness_score > ananya.readiness_score, (
        f"CSV calibration: Karthik ({karthik.readiness_score}) must > Ananya ({ananya.readiness_score}) on Google DS"
    )


def test_csv_loader_skips_unprocessed_rows():
    """Rows with processed != 'true' must be excluded (rows 93 & 108 in the current CSV)."""
    from app.talent_check.scoring import load_company_levels_from_csv
    entries = load_company_levels_from_csv()
    companies = {e["company"] for e in entries}
    # These two companies have processed=false in the current CSV snapshot
    assert "Byju's" not in companies, "Unprocessed Byju's row must be excluded"
    # Simplilearn may appear with a different exact name; just verify processed=false rows
    # aren't duplicated — total entry count must be <= 114 * max_roles (i.e. < 250)
    assert len(entries) < 250, "Suspiciously many entries — unprocessed rows may have leaked"


# ===========================================================================
# 6. CONTRACT SHAPE TESTS (Part 2 step 2 & 3)
# ===========================================================================

def test_response_keys_match_contract():
    """
    TalentCheckResult must have the mandatory contract keys.
    Verifies: company, skillset_gap, readiness_score, and 12 mandatory codes.
    """
    from app.schemas import TWELVE_SKILLSETS
    from app.talent_check.scoring import load_company_levels_from_csv, find_level_entry
    levels = load_company_levels_from_csv()
    g_swe = find_level_entry("Google LLC", "Software Engineer", levels)
    result = _score("ananya-rao", g_swe, "Google LLC")

    # Top-level mandatory keys
    assert hasattr(result, "company"),       "missing 'company'"
    assert hasattr(result, "skillset_gap"),  "missing 'skillset_gap'"
    assert hasattr(result, "readiness_score"), "missing 'readiness_score'"

    # All 12 codes present
    codes = {g.category_code for g in result.skillset_gap}
    for code in TWELVE_SKILLSETS:
        assert code in codes, f"code {code!r} missing from skillset_gap"

    # Each gap item has mandatory typed fields
    for g in result.skillset_gap:
        assert isinstance(g.category_code,   str),  f"{g.category_code}: category_code not str"
        assert isinstance(g.required_level,   int),  f"{g.category_code}: required_level not int"
        assert isinstance(g.candidate_level,  int),  f"{g.category_code}: candidate_level not int"
        assert isinstance(g.gap,              bool), f"{g.category_code}: gap not bool"


def test_all_levels_in_range_across_all_companies_and_roles():
    """
    For every company+role in the CSV loader:
      - required_level must be an int in [1, 10]   (contract says 1-10, 0 is never valid)
      - candidate_level must be an int in [0, 10]   (0 = no evidence, allowed)
      - readiness_score must be an int in [0, 100]
    Tested across all 4 fixture candidates × all loaded entries.
    """
    from app.schemas import CandidateProfile, TWELVE_SKILLSETS
    from app.talent_check.scoring import load_company_levels_from_csv, score
    entries = load_company_levels_from_csv()
    slugs = ["ananya-rao", "karthik-subramaniam", "priya-menon", "rohan-verma"]
    profiles = {s: _load_profile(s) for s in slugs}

    for entry in entries:
        co = entry["company"]
        ro = entry["role"]
        lvls = entry["levels"]
        for slug, profile in profiles.items():
            result = score(profile, lvls, co)

            assert isinstance(result.readiness_score, int), (
                f"{co}/{ro}/{slug}: readiness_score is not int"
            )
            assert 0 <= result.readiness_score <= 100, (
                f"{co}/{ro}/{slug}: readiness_score={result.readiness_score} out of [0,100]"
            )
            assert len(result.skillset_gap) == 12, (
                f"{co}/{ro}: skillset_gap has {len(result.skillset_gap)} items, expected 12"
            )
            for g in result.skillset_gap:
                assert isinstance(g.required_level, int), (
                    f"{co}/{ro}/{g.category_code}: required_level not int"
                )
                assert 1 <= g.required_level <= 10, (
                    f"{co}/{ro}/{g.category_code}: required_level={g.required_level} not in [1,10]"
                )
                assert isinstance(g.candidate_level, int), (
                    f"{co}/{ro}/{slug}/{g.category_code}: candidate_level not int"
                )
                assert 0 <= g.candidate_level <= 10, (
                    f"{co}/{ro}/{slug}/{g.category_code}: candidate_level={g.candidate_level} not in [0,10]"
                )


# ===========================================================================
# 7. EXTRA FIELDS TEST (Part 2 step 4)
# ===========================================================================

def test_skillset_gap_extra_fields_populated_from_csv():
    """
    When scoring from CSV-loaded levels, each SkillsetGap must have:
      - company_aggregate_level: int (the raw CSV value before role weighting)
      - role_weight: float (the fraction applied to produce required_level)
    Both must be consistent: round(aggregate * weight) == required_level (within rounding).
    """
    from app.talent_check.scoring import (
        load_company_levels_from_csv, find_full_entry, score
    )
    levels = load_company_levels_from_csv()
    entry = find_full_entry("Google LLC", "Software Engineer", levels)
    assert entry is not None, "Google LLC / Software Engineer entry not found"

    profile = _load_profile("ananya-rao")
    result = score(
        profile,
        entry["levels"],
        "Google LLC",
        company_aggregates=entry.get("aggregate"),
        role_weights_used=entry.get("weights_used"),
    )

    for g in result.skillset_gap:
        assert g.company_aggregate_level is not None, (
            f"{g.category_code}: company_aggregate_level is None — should be populated from CSV"
        )
        assert g.role_weight is not None, (
            f"{g.category_code}: role_weight is None — should be populated from CSV"
        )
        assert isinstance(g.company_aggregate_level, int), (
            f"{g.category_code}: company_aggregate_level is not int"
        )
        assert isinstance(g.role_weight, float), (
            f"{g.category_code}: role_weight is not float"
        )
        # Consistency: required_level should be round(aggregate * weight), at most ±1 due to rounding
        expected = max(1, round(g.company_aggregate_level * g.role_weight))
        assert abs(g.required_level - expected) <= 1, (
            f"{g.category_code}: required_level={g.required_level} but "
            f"round({g.company_aggregate_level}*{g.role_weight})={expected}"
        )


def test_extra_fields_none_when_not_using_csv():
    """
    When score() is called WITHOUT aggregate/weights (e.g. from JSON or placeholder),
    company_aggregate_level and role_weight must both be None.
    """
    from app.schemas import CandidateProfile
    from app.talent_check.scoring import score
    profile = CandidateProfile(
        candidate_id="test-none-extras",
        name="Test Candidate",
        skills=[],
    )
    plain_levels = {"DSA": 8, "COD": 8, "OOD": 6, "APTI": 5, "COMM": 6,
                    "AI": 1, "CLOUD": 3, "SQL": 3, "SWE": 7, "SYSD": 7,
                    "NETW": 6, "OS": 6}
    result = score(profile, plain_levels, "SomeCompany")  # no aggregates/weights passed
    for g in result.skillset_gap:
        assert g.company_aggregate_level is None, (
            f"{g.category_code}: company_aggregate_level should be None when not from CSV"
        )
        assert g.role_weight is None, (
            f"{g.category_code}: role_weight should be None when not from CSV"
        )


def test_json_loader_preserves_aggregate_and_weights_for_all_demo_roles(monkeypatch):
    """
    When the JSON file is the source (storage returns None, JSON file exists),
    every entry must have 'aggregate' and 'weights_used', and score() must
    populate company_aggregate_level and role_weight on all 12 SkillsetGap items.
    """
    import app.talent_check.scoring as sc
    from app.talent_check.scoring import load_company_levels_with_source, find_full_entry
    from app.schemas import CandidateProfile

    # Patch storage.load to return None so stage-1 (Supabase) is skipped
    monkeypatch.setattr(sc, "_ACTIVE_SOURCE", None)
    with monkeypatch.context() as mp:
        # Import here so we can patch within the scoring module's own storage reference
        from app.core import storage as st_mod
        original_load = st_mod.load
        mp.setattr(st_mod, "load", lambda *_a, **_k: None)   # stage-1 returns nothing
        levels, source = load_company_levels_with_source()

    assert source == "json", f"Expected source='json' but got {source!r} (is JSON file missing?)"

    demo_roles = [
        ("Google LLC", "Software Engineer"),
        ("Google LLC", "Data Scientist"),
        ("Microsoft Corporation", "Software Engineer"),
        ("Microsoft Corporation", "Data Analyst"),
        ("Oracle Financial Services Software", "Associate Software Engineer"),
        ("Oracle Financial Services Software", "Application Support Analyst"),
    ]
    profile = CandidateProfile(candidate_id="json-source-test", name="Test Candidate", skills=[])
    for company, role in demo_roles:
        entry = find_full_entry(company, role, levels)
        assert entry is not None, f"{company} / {role} missing from JSON loader output"
        assert "aggregate" in entry, f"{company}/{role}: 'aggregate' key missing from JSON entry"
        assert "weights_used" in entry, f"{company}/{role}: 'weights_used' key missing from JSON entry"

        result = score(
            profile,
            entry["levels"],
            company,
            company_aggregates=entry.get("aggregate"),
            role_weights_used=entry.get("weights_used"),
            data_source=source,
        )
        assert result.data_source == "json", (
            f"{company}/{role}: expected data_source='json' got {result.data_source!r}"
        )
        for g in result.skillset_gap:
            assert g.company_aggregate_level is not None, (
                f"{company}/{role}/{g.category_code}: company_aggregate_level is None from JSON source"
            )
            assert g.role_weight is not None, (
                f"{company}/{role}/{g.category_code}: role_weight is None from JSON source"
            )


def test_data_source_field_populated_in_result():
    """score() must populate data_source in TalentCheckResult when passed."""
    from app.talent_check.scoring import load_company_levels_from_csv, find_full_entry
    levels = load_company_levels_from_csv()
    entry = find_full_entry("Google LLC", "Software Engineer", levels)
    profile = _load_profile("ananya-rao")

    result = score(
        profile, entry["levels"], "Google LLC",
        company_aggregates=entry.get("aggregate"),
        role_weights_used=entry.get("weights_used"),
        data_source="csv",
    )
    assert result.data_source == "csv", f"Expected 'csv', got {result.data_source!r}"

    result2 = score(profile, entry["levels"], "Google LLC")
    assert result2.data_source is None, "data_source should be None when not explicitly passed"


def test_csv_deduplication_zs_associates():
    """ZS Associates, Inc. appears twice in CSV (rows 33 and 102). Only one entry must be emitted."""
    from app.talent_check.scoring import load_company_levels_from_csv
    entries = load_company_levels_from_csv()
    zs_entries = [e for e in entries if e["company"] == "ZS Associates, Inc."]
    assert len(zs_entries) == 1, (
        f"Expected exactly 1 entry for ZS Associates, Inc., got {len(zs_entries)}. "
        "Deduplication in load_company_levels_from_csv() may have failed."
    )


def test_distinct_company_count_is_113():
    """After deduplication, the CSV loader must yield exactly 113 distinct companies."""
    from app.talent_check.scoring import load_company_levels_from_csv
    entries = load_company_levels_from_csv()
    distinct = {e["company"] for e in entries}
    assert len(distinct) == 113, (
        f"Expected 113 distinct companies (114 processed - 1 ZS duplicate), got {len(distinct)}"
    )
