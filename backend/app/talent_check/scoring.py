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

Company levels source (priority order):
  1. Supabase / local storage mirror (seeded by seed_supabase.py)
  2. backend/data/talent_check_company_skillsets.json  (if manually placed)
  3. backend/app/talent_check/staging_company_skill_levels_rows.csv  (primary local fallback)
  4. backend/data/talent_check_company_skillsets.PLACEHOLDER.json

The CSV contains one aggregate row per company (116 rows).
Because the CSV has no role column, role-specific levels are derived by applying
_ROLE_WEIGHTS profiles: each weight is the fraction of the company aggregate that
applies to that role.  The 6 demo roles (2 per in-scope company) are pre-configured;
all other CSV companies get a single "Software Engineer" entry with raw levels.
"""

from __future__ import annotations

import csv
import json
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

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

# Paths
_MODULE_DIR  = Path(__file__).resolve().parent
_DATA_DIR    = _MODULE_DIR.parents[1] / "data"
_REAL_FILE   = _DATA_DIR / "talent_check_company_skillsets.json"
_PLACEHOLDER = _DATA_DIR / "talent_check_company_skillsets.PLACEHOLDER.json"
_CSV_FILE    = _MODULE_DIR / "staging_company_skill_levels_rows.csv"

# ---------------------------------------------------------------------------
# CSV column name  ->  RADIX category code
# ---------------------------------------------------------------------------
_CSV_COL_TO_CODE: dict[str, str] = {
    "coding":                                 "COD",
    "data_structures_and_algorithms":         "DSA",
    "object_oriented_programming_and_design": "OOD",
    "aptitude_and_problem_solving":           "APTI",
    "communication_skills":                   "COMM",
    "ai_native_engineering":                  "AI",
    "devops_and_cloud":                       "CLOUD",
    "sql_and_design":                         "SQL",
    "software_engineering":                   "SWE",
    "system_design_and_architecture":         "SYSD",
    "computer_networking":                    "NETW",
    "operating_system":                       "OS",
}

# ---------------------------------------------------------------------------
# CSV company name  ->  canonical display name
# (Only the three in-scope companies differ; all others pass through unchanged.)
# ---------------------------------------------------------------------------
_COMPANY_ALIASES: dict[str, str] = {
    "Google LLC (Subsidiary of Alphabet Inc.)":  "Google LLC",
    "Oracle Financial Services Software Limited": "Oracle Financial Services Software",
    # "Microsoft Corporation" matches exactly — no alias needed
}

# ---------------------------------------------------------------------------
# Role-weight profiles.
# Each weight is the fraction of the company's aggregate CSV level to require
# for that specific role.  1.0 = full company bar; 0.1 = barely matters.
#
# These weights are calibrated so that all five calibration test orderings pass
# (Ananya > Karthik on SWE; Karthik > Ananya on DS; Priya Oracle > Priya Google;
#  Rohan >= all on every role tested).  Verified by scratch/verify_role_weights.py.
# ---------------------------------------------------------------------------
_ROLE_WEIGHTS: dict[str, dict[str, float]] = {
    "Software Engineer": {
        "DSA":  1.0, "COD":  1.0, "OOD":  1.0, "SWE":  1.0, "SYSD": 1.0,
        "OS":   1.0, "NETW": 0.8, "APTI": 0.7,
        "COMM": 0.6, "CLOUD": 0.5, "SQL":  0.3, "AI":   0.1,
    },
    "Data Scientist": {
        "AI":   1.0, "SQL":  1.0, "APTI": 1.0, "COMM": 1.0, "COD":  0.7,
        "SWE":  0.5, "DSA":  0.4, "CLOUD": 0.4, "OOD":  0.2,
        "OS":   0.1, "NETW": 0.1, "SYSD": 0.3,
    },
    "Associate Software Engineer": {
        "COD":  0.85, "SQL": 0.85, "DSA":  0.85, "OOD":  0.85, "SWE":  0.85,
        "OS":   0.75, "APTI": 0.85, "COMM": 0.85,
        "CLOUD": 0.6, "NETW": 0.4, "SYSD": 0.4,  "AI":   0.2,
    },
    "Application Support Analyst": {
        "SQL":  0.5, "OS":   0.5,  "NETW": 0.5, "APTI": 0.6, "COMM": 0.85,
        "COD":  0.2, "DSA":  0.2,  "SWE":  0.3, "OOD":  0.1,
        "SYSD": 0.1, "CLOUD": 0.2, "AI":   0.1,
    },
    "Data Analyst": {
        "SQL":  1.0, "AI":   0.8, "APTI": 0.9, "COMM": 1.0, "COD":  0.5,
        "SWE":  0.4, "DSA":  0.3, "OOD":  0.2, "CLOUD": 0.3,
        "OS":   0.1, "NETW": 0.1, "SYSD": 0.2,
    },
}

# In-scope companies for the hackathon demo: canonical name -> list of demo roles.
# These get one entry per role with role-weight applied.
# Every other CSV company gets one "Software Engineer" entry with raw aggregate levels.
_DEMO_ROLES: dict[str, list[str]] = {
    "Google LLC":                        ["Software Engineer", "Data Scientist"],
    "Microsoft Corporation":             ["Software Engineer", "Data Analyst"],
    "Oracle Financial Services Software":["Associate Software Engineer", "Application Support Analyst"],
}



# ---------------------------------------------------------------------------
# CSV parsing helpers
# ---------------------------------------------------------------------------

def _parse_level(value: str) -> int:
    """
    Extract the numeric part from a cell like '5-AP', '9 - EV', '7 - AS'.
    The suffix (AP, EV, AS, CU, CR) is the company acronym — NOT a proficiency
    classification.  We only keep the integer before the dash.
    Returns 0 if the value is blank or unparseable.
    """
    m = re.match(r"\s*(\d+)", value.strip())
    return int(m.group(1)) if m else 0


def _apply_role_weights(
    aggregate: dict[str, int],
    role: str,
) -> tuple[dict[str, int], dict[str, float]]:
    """
    Given a company's aggregate required levels from the CSV,
    apply the role-weight profile and return (level_dict, weights_used).

    For roles NOT listed in _ROLE_WEIGHTS (generic companies), all weights
    default to 1.0 — the aggregate levels are used as-is.
    max(..., 1) ensures we never emit a 0 even for very small weights.

    Returns:
        levels      — {RADIX_CODE: required_level}  (what goes into scoring)
        weights_used — {RADIX_CODE: weight}          (stored for UI transparency)
    """
    weights = _ROLE_WEIGHTS.get(role, {c: 1.0 for c in TWELVE_SKILLSETS})
    levels = {
        cat: max(1, round(aggregate.get(cat, 0) * weights.get(cat, 1.0)))
        for cat in TWELVE_SKILLSETS
    }
    return levels, weights


def load_company_levels_from_csv() -> list[dict]:
    """
    Read staging_company_skill_levels_rows.csv and return the standard list:
      [
        {
          "company": "...",
          "role":    "...",
          "levels":  {"DSA": 9, "COD": 8, ...},   # role-weighted required levels
          "aggregate":  {"DSA": 9, ...},           # raw CSV values (for UI transparency)
          "weights_used": {"DSA": 1.0, ...},       # role-weight fractions applied
        }, ...
      ]

    Algorithm:
      1. Parse each row; extract the integer from cells like '5-AP' and '9 - EV'.
      2. Log a WARNING for every row skipped because processed != 'true'.
      3. Log a WARNING and skip duplicate canonical names (keeps first occurrence).
      4. Apply the canonical company alias map for the 3 in-scope companies.
      5. In-scope companies: emit one entry per demo role, with role-weights applied.
      6. All other companies: emit one "Software Engineer" entry with raw levels.
    """
    if not _CSV_FILE.exists():
        raise FileNotFoundError(f"CSV not found: {_CSV_FILE}")

    entries: list[dict] = []
    seen_canonicals: set[str] = set()   # track company names already emitted

    with open(_CSV_FILE, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row.get("processed", "").strip().lower() != "true":
                csv_row_num = reader.line_num - 1
                company_name = row.get("companies", "(unknown)").strip()
                err_msg = row.get("error_message", "").strip()[:120]
                log.warning(
                    "CSV row %d skipped (processed=false): company=%r error=%r",
                    csv_row_num, company_name, err_msg,
                )
                continue

            raw_name = row.get("companies", "").strip()
            if not raw_name:
                continue

            # Parse the 12 aggregate skill levels from this company's row
            aggregate: dict[str, int] = {
                code: _parse_level(row.get(col, ""))
                for col, code in _CSV_COL_TO_CODE.items()
            }

            # Resolve canonical display name (renames the 3 in-scope companies)
            canonical = _COMPANY_ALIASES.get(raw_name, raw_name)

            # Skip duplicate canonical names — keep the first occurrence
            if canonical in seen_canonicals:
                csv_row_num = reader.line_num - 1
                log.warning(
                    "CSV row %d duplicate skipped: company=%r already seen (different levels possible)",
                    csv_row_num, canonical,
                )
                continue
            seen_canonicals.add(canonical)

            if canonical in _DEMO_ROLES:
                # In-scope company: produce one entry per demo role with weights applied
                for role in _DEMO_ROLES[canonical]:
                    levels, weights_used = _apply_role_weights(aggregate, role)
                    entries.append({
                        "company":      canonical,
                        "role":         role,
                        "levels":       levels,
                        "aggregate":    aggregate,      # raw CSV values
                        "weights_used": weights_used,   # fractions applied
                    })
            else:
                # Generic company: single entry, raw aggregate, no weighting (all 1.0)
                entries.append({
                    "company":      canonical,
                    "role":         "Software Engineer",
                    "levels":       aggregate,   # raw levels used directly for generics
                    "aggregate":    aggregate,
                    "weights_used": {c: 1.0 for c in TWELVE_SKILLSETS},
                })

    return entries


# ---------------------------------------------------------------------------
# Company-levels loader — 4-stage fallback chain
# ---------------------------------------------------------------------------

def load_company_levels_with_source() -> tuple[list[dict], str]:
    """
    Load company/role levels and return (entries, data_source_tag).

    data_source_tag values:
      'supabase'    — data came from Supabase documents table (live or cached)
      'json'        — data came from talent_check_company_skillsets.json
      'csv'         — data came from staging_company_skill_levels_rows.csv
      'placeholder' — data came from the PLACEHOLDER JSON (last resort)

    Priority order:
      1. Supabase / local storage mirror (seeded by seed_supabase.py)
      2. backend/data/talent_check_company_skillsets.json
      3. staging_company_skill_levels_rows.csv
      4. backend/data/talent_check_company_skillsets.PLACEHOLDER.json
    """
    # 1. Try Supabase / local storage mirror
    try:
        from ..core import storage  # late import keeps scoring.py clean during unit tests
        raw, source = storage.load_with_source("company_skillsets", "all")
        if raw and "roles" in raw:
            return raw["roles"], source or "json"
    except Exception as e:
        log.warning("Unable to load company skillsets from storage: %s", e)

    # 2. Try the real JSON file (manually provided / generated by export script)
    if _REAL_FILE.exists():
        data = json.loads(_REAL_FILE.read_text(encoding="utf-8"))
        return data["roles"], "json"

    # 3. Try the CSV snapshot
    try:
        return load_company_levels_from_csv(), "csv"
    except Exception as e:
        log.warning("Unable to load company skillsets from CSV: %s", e)

    # 4. Last resort: placeholder JSON
    data = json.loads(_PLACEHOLDER.read_text(encoding="utf-8"))
    return data["roles"], "placeholder"


# Track the active source so the router can log it once at startup
_ACTIVE_SOURCE: str | None = None


def load_company_levels() -> list[dict]:
    """Compatibility wrapper — returns entries without source metadata."""
    global _ACTIVE_SOURCE
    entries, source = load_company_levels_with_source()
    if _ACTIVE_SOURCE is None:
        _ACTIVE_SOURCE = source
        log.info(
            "[TalentCheck] Company levels loaded from source=%r  entries=%d",
            source, len(entries),
        )
    return entries



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
    Backward-compatible: returns only the levels dict.
    """
    for entry in levels:
        if entry["company"] == company and entry["role"] == role:
            return entry["levels"]
    return None


def find_full_entry(company: str, role: str, levels: list[dict]) -> dict | None:
    """
    Like find_level_entry but returns the FULL entry dict, including:
      'levels'       — role-weighted required levels
      'aggregate'    — raw CSV values (None for JSON-sourced data)
      'weights_used' — role-weight fractions (None for JSON-sourced data)
    Returns None if not found.
    """
    for entry in levels:
        if entry["company"] == company and entry["role"] == role:
            return entry
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
    company_levels: dict[str, int],              # role-weighted required levels
    company: str,
    company_aggregates: dict[str, int] | None = None,  # raw CSV values (for UI)
    role_weights_used: dict[str, float] | None = None, # fractions applied (for UI)
    data_source: str | None = None,                    # "supabase"|"json"|"csv"|"placeholder"
) -> TalentCheckResult:
    """
    Compare a CandidateProfile against one company/role's required levels.

    Pure function: same inputs always produce the same output.
    Uses only the 12 scored skillsets (OTHER is ignored, per the spec).

    readiness_score = round(100 * sum(min(cand, req)) / sum(req))  over the 12 skillsets.
      — exceeding the bar in one category can NOT hide a gap elsewhere.

    Optional extra args (populated when loading from the CSV):
      company_aggregates  — raw CSV integer per category, stored in SkillsetGap for UI
      role_weights_used   — fraction applied per category, stored in SkillsetGap for UI
    """
    gaps: list[SkillsetGap] = []
    sum_min = 0     # numerator:   sum of min(candidate, required)
    sum_req = 0     # denominator: sum of required levels

    for cat in TWELVE_SKILLSETS:
        required  = company_levels.get(cat, 0)   # default 0 if company doesn't care
        candidate, explanation = _candidate_level_for_category(profile.skills, cat)

        gap_exists = candidate < required
        gap_size   = max(0, required - candidate)

        gaps.append(SkillsetGap(
            category_code=cat,           # type: ignore[arg-type]
            required_level=required,
            candidate_level=candidate,
            gap=gap_exists,
            gap_size=gap_size,
            explanation=explanation,
            # Additive v1.1 fields — None when data comes from JSON/storage
            company_aggregate_level=(
                company_aggregates.get(cat) if company_aggregates else None
            ),
            role_weight=(
                role_weights_used.get(cat) if role_weights_used else None
            ),
        ))

        sum_min += min(candidate, required)
        sum_req += required

    # Avoid division-by-zero (extremely unlikely: no required levels set at all)
    readiness = round(100 * sum_min / sum_req) if sum_req > 0 else 0

    formula = (
        "readiness = round(100 x sum(min(candidate_level, required_level)) / sum(required_level)) "
        "over the 12 skillsets. "
        "candidate_level: strongest skill in category (high=7, med=5, low=3) "
        "+ 1 per additional skill in same category (max +3 bonus), capped at 10. "
        "required_level = round(company_aggregate x role_weight); "
        "role weights emphasise COD/DSA/OS for SWE and AI/SQL/COMM for Data Scientist."
    )

    return TalentCheckResult(
        company=company,
        candidate_id=profile.candidate_id,
        skillset_gap=gaps,
        readiness_score=readiness,
        scoring_method=formula,
        data_source=data_source,
    )
