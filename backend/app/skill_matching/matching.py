"""
Skill Matching Engine (Role 5).

Implements 4-tiered matching:
  Tier 1: Exact matching (normalized string comparison, similarity 1.0)
  Tier 2: Alias matching (canonical dictionary resolution, similarity 0.95)
  Tier 3: Fuzzy matching (RapidFuzz token_set_ratio >= 88, similarity 0.88-1.0)
  Tier 4: Semantic matching via LLM (adjudication for leftovers, similarity >= 0.70)

Includes:
  - Disk caching in data/cache/ for LLM responses
  - Safe deterministic fallback if the LLM fails or is unavailable
  - Weighted match score calculation (Required=2, Preferred=1, Unspecified=1)
  - Prioritized missing skill identification with actionable suggestions
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Optional, Sequence
from pydantic import BaseModel, Field, ValidationError
from rapidfuzz import fuzz

from app.core import llm
from app.schemas import (
    CATEGORY_CODES,
    CategoryCode,
    Importance,
    MatchedSkill,
    MissingSkill,
    Skill,
    SkillMatchResult,
)

log = logging.getLogger("skill_matching")

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache"
FUZZY_THRESHOLD = 88
SEMANTIC_THRESHOLD = 0.70

# Maintainable alias mapping: normalized abbreviation/alternative -> canonical term
ALIASES: dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "golang": "go",
    "postgres": "postgresql",
    "psql": "postgresql",
    "mongo": "mongodb",
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "k8s": "kubernetes",
    "tf": "tensorflow",
    "reactjs": "react",
    "react": "react",
    "nodejs": "nodejs",
    "node": "nodejs",
    "aws": "amazon web services",
    "gcp": "google cloud platform",
    "dsa": "data structures and algorithms",
    "oop": "object oriented programming",
    "ood": "object oriented design",
}

SEMANTIC_SYSTEM_PROMPT = (
    "You are an expert technical recruiter and software architect evaluating candidate skills against job requirements.\n"
    "Your task: evaluate whether any of the UNMATCHED job description skills can be satisfied by the UNMATCHED candidate skills.\n\n"
    "Rules:\n"
    "1. Only match genuine technical equivalences or direct domain substitutions (e.g. 'Amazon EC2' satisfies 'Cloud Compute VMs').\n"
    "2. Do NOT match loosely related technologies (e.g. 'Docker' is NOT 'Kubernetes'; 'scikit-learn' is NOT generic 'Machine Learning'; 'React' is NOT 'React Native').\n"
    "3. Similarity must be a float between 0.0 and 1.0 (1.0 = fully interchangeable, 0.7 = strongly equivalent, <0.7 = weak or partial).\n"
    "4. Each candidate skill can match at most ONE job skill.\n"
    "5. Return ONLY a valid JSON object in this exact format with no markdown, no quotes around the JSON, and no chatter:\n"
    '{"matches": [{"jd_skill": "string", "candidate_skill": "string", "similarity": 0.85, "reason": "short explanation"}]}\n'
    'If there are no valid matches, return: {"matches": []}'
)


class SemanticMatchItem(BaseModel):
    jd_skill: str = Field(min_length=1)
    candidate_skill: str = Field(min_length=1)
    similarity: float = Field(ge=0.0, le=1.0)
    reason: Optional[str] = None


class SemanticMatchOutput(BaseModel):
    matches: list[SemanticMatchItem] = Field(default_factory=list)


def parse_json_reply(text: str) -> dict:
    """Safely pull the first JSON object out of an LLM reply, handling markdown fences and surrounding commentary."""
    clean = re.sub(r"```(?:json)?", "", text)
    start, end = clean.find("{"), clean.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No valid JSON object found in LLM response.")
    return json.loads(clean[start:end + 1])


def normalize_skill(skill: str) -> str:
    """
    Normalize skill names for consistent comparison:
    - Lowercase and trim whitespace
    - Normalize '.js' extensions (e.g., 'Node.js' -> 'nodejs', 'React.js' -> 'reactjs')
    - Strip punctuation like quotes, commas, brackets, colons
    - Replace dashes, underscores, slashes with spaces
    - Preserve critical language markers (+ for C++, # for C#)
    - Collapse multiple whitespace
    """
    if not skill:
        return ""
    text = skill.strip().lower()
    text = re.sub(r"(\w+)\.js\b", r"\1js", text)
    text = re.sub(r"[,:;()\[\]{}'\"`]", "", text)
    text = re.sub(r"[-_/]+", " ", text)
    text = re.sub(r"\.(?!\w)", "", text)
    text = text.replace(".", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def resolve_alias(skill: str) -> str:
    """Resolve a skill name to its canonical alias form after normalization."""
    normalized = normalize_skill(skill)
    return ALIASES.get(normalized, normalized)


def _get_skill_name(item: str | Skill) -> str:
    """Extract skill name whether item is a Skill instance or a string."""
    return item.skill_name if isinstance(item, Skill) else str(item)


def exact_match(
    candidate_skills: Sequence[str | Skill],
    job_skills: Sequence[str | Skill],
) -> list[MatchedSkill]:
    """Find exact matches where normalized skill names match identically (similarity 1.0)."""
    matches: list[MatchedSkill] = []
    used_cand_indices: set[int] = set()

    for jd in job_skills:
        jd_name = _get_skill_name(jd)
        norm_jd = normalize_skill(jd_name)
        if not norm_jd:
            continue

        for idx, cand in enumerate(candidate_skills):
            if idx in used_cand_indices:
                continue
            cand_name = _get_skill_name(cand)
            if normalize_skill(cand_name) == norm_jd:
                used_cand_indices.add(idx)
                matches.append(
                    MatchedSkill(
                        jd_skill=jd_name,
                        candidate_skill=cand_name,
                        match_type="exact",
                        similarity=1.0,
                    )
                )
                break
    return matches


def alias_match(
    candidate_skills: Sequence[str | Skill],
    job_skills: Sequence[str | Skill],
) -> list[MatchedSkill]:
    """Find alias matches where resolved aliases match, but normalized strings differ (similarity 0.95)."""
    matches: list[MatchedSkill] = []
    used_cand_indices: set[int] = set()

    for jd in job_skills:
        jd_name = _get_skill_name(jd)
        norm_jd = normalize_skill(jd_name)
        alias_jd = resolve_alias(jd_name)
        if not alias_jd:
            continue

        for idx, cand in enumerate(candidate_skills):
            if idx in used_cand_indices:
                continue
            cand_name = _get_skill_name(cand)
            norm_cand = normalize_skill(cand_name)
            if norm_cand != norm_jd and resolve_alias(cand_name) == alias_jd:
                used_cand_indices.add(idx)
                matches.append(
                    MatchedSkill(
                        jd_skill=jd_name,
                        candidate_skill=cand_name,
                        match_type="alias",
                        similarity=0.95,
                    )
                )
                break
    return matches


def fuzzy_match(
    candidate_skills: Sequence[str | Skill],
    job_skills: Sequence[str | Skill],
    threshold: int = FUZZY_THRESHOLD,
) -> list[MatchedSkill]:
    """Fuzzy match remaining skills using RapidFuzz token_set_ratio >= threshold (0.0-1.0)."""
    matches: list[MatchedSkill] = []
    used_cand_indices: set[int] = set()

    for jd in job_skills:
        jd_name = _get_skill_name(jd)
        norm_jd = normalize_skill(jd_name)
        if not norm_jd:
            continue

        best_score = -1.0
        best_cand_idx = -1
        best_cand_name = ""

        for idx, cand in enumerate(candidate_skills):
            if idx in used_cand_indices:
                continue
            cand_name = _get_skill_name(cand)
            norm_cand = normalize_skill(cand_name)
            score = float(fuzz.token_set_ratio(norm_jd, norm_cand))
            if score > best_score:
                best_score = score
                best_cand_idx = idx
                best_cand_name = cand_name

        if best_score >= threshold and best_cand_idx != -1:
            used_cand_indices.add(best_cand_idx)
            similarity = round(best_score / 100.0, 2)
            matches.append(
                MatchedSkill(
                    jd_skill=jd_name,
                    candidate_skill=best_cand_name,
                    match_type="fuzzy",
                    similarity=min(1.0, max(0.0, similarity)),
                )
            )
    return matches


def get_semantic_cache_path(
    unmatched_jds: Sequence[Skill],
    available_cands: Sequence[Skill],
) -> Path:
    """Generate a deterministic disk cache path based on the sorted skill names."""
    jd_names = ",".join(sorted(normalize_skill(s.skill_name) for s in unmatched_jds))
    cand_names = ",".join(sorted(normalize_skill(s.skill_name) for s in available_cands))
    digest = hashlib.sha256(f"semantic_v1|{jd_names}|{cand_names}".encode("utf-8")).hexdigest()[:24]
    return CACHE_DIR / f"semantic_{digest}.json"


def adjudicate_semantic_matches(
    unmatched_jds: Sequence[Skill],
    available_cands: Sequence[Skill],
    threshold: float = SEMANTIC_THRESHOLD,
    use_cache: bool = True,
) -> list[SemanticMatchItem]:
    """
    Call LLM in a single batched request to adjudicate equivalences between leftovers.
    Uses disk caching and falls back safely to [] if the LLM fails or returns invalid data.
    """
    if not unmatched_jds or not available_cands:
        return []

    cache_file = get_semantic_cache_path(unmatched_jds, available_cands)

    # 1. Try reading from disk cache
    if use_cache and cache_file.exists():
        try:
            raw = cache_file.read_text(encoding="utf-8")
            cached_output = SemanticMatchOutput.model_validate_json(raw)
            return [m for m in cached_output.matches if m.similarity >= threshold]
        except (json.JSONDecodeError, ValidationError, OSError) as e:
            log.warning("Cache file %s corrupted or unreadable (%s); regenerating via LLM.", cache_file.name, e)

    # 2. Prepare single batched prompt
    jd_text = "\n".join(f"- {s.skill_name} ({s.category_code})" for s in unmatched_jds)
    cand_text = "\n".join(f"- {s.skill_name} ({s.category_code})" for s in available_cands)

    messages = [
        ("system", SEMANTIC_SYSTEM_PROMPT),
        ("human", f"UNMATCHED JOB SKILLS:\n{jd_text}\n\nUNMATCHED CANDIDATE SKILLS:\n{cand_text}"),
    ]

    # 3. Call ask() with fallback
    try:
        reply = llm.ask(messages)
        parsed = parse_json_reply(reply)
        validated = SemanticMatchOutput.model_validate(parsed)
    except Exception as err:
        log.warning("LLM semantic adjudication failed (%s). Safely falling back to deterministic results.", err)
        return []

    # 4. Save to disk cache
    if use_cache:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(validated.model_dump_json(indent=2), encoding="utf-8")
        except OSError as e:
            log.warning("Could not write cache file %s: %s", cache_file.name, e)

    return [m for m in validated.matches if m.similarity >= threshold]


def calculate_match_score(
    matched_job_skills: Sequence[Skill],
    all_job_skills: Sequence[Skill],
) -> int:
    """Calculate weighted match score: Required=2, Preferred/Unspecified=1."""
    if not all_job_skills:
        return 0

    def _weight(s: Skill) -> int:
        if s.importance == "required":
            return 2
        return 1

    total_weight = sum(_weight(s) for s in all_job_skills)
    if total_weight == 0:
        return 0

    matched_weight = sum(_weight(s) for s in matched_job_skills)
    return int(round(100.0 * matched_weight / total_weight))


def prioritize_missing_skills(
    unmatched_job_skills: Sequence[Skill],
) -> list[MissingSkill]:
    """Order missing skills by importance, category code, and name."""
    cat_order = {cat: i for i, cat in enumerate(CATEGORY_CODES)}

    def _sort_key(s: Skill):
        if s.importance == "required":
            imp_rank = 0
        elif s.importance == "preferred":
            imp_rank = 1
        else:
            imp_rank = 2
        c_rank = cat_order.get(s.category_code, 999)
        return (imp_rank, c_rank, s.skill_name.lower())

    sorted_skills = sorted(unmatched_job_skills, key=_sort_key)
    missing: list[MissingSkill] = []
    for s in sorted_skills:
        suggestion = f"Build a small project or complete targeted exercises using {s.skill_name}."
        missing.append(
            MissingSkill(
                skill_name=s.skill_name,
                category_code=s.category_code,
                importance=s.importance,
                suggestion=suggestion,
            )
        )
    return missing


def match_skills_pipeline(
    candidate_skills: Sequence[Skill],
    job_skills: Sequence[Skill],
    fuzzy_threshold: int = FUZZY_THRESHOLD,
    semantic_threshold: float = SEMANTIC_THRESHOLD,
    use_llm: bool = True,
    use_cache: bool = True,
) -> tuple[list[MatchedSkill], list[MissingSkill], int]:
    """
    Execute 4-tier matching pipeline:
      Tier 1: Exact matches (1.0)
      Tier 2: Alias matches (0.95)
      Tier 3: Fuzzy matches (rapidfuzz >= 88)
      Tier 4: Semantic LLM matches (similarity >= 0.70)
    """
    if not job_skills:
        return [], [], 0

    matched_skills: list[MatchedSkill] = []
    matched_jd_skills: list[Skill] = []
    available_candidates: list[Skill] = list(candidate_skills)
    remaining_jds: list[Skill] = list(job_skills)

    def _consume_match(cand_skill_name: str, jd_skill: Skill, match_type: str, sim: float):
        matched_skills.append(
            MatchedSkill(
                jd_skill=jd_skill.skill_name,
                candidate_skill=cand_skill_name,
                match_type=match_type,  # type: ignore[arg-type]
                similarity=sim,
            )
        )
        matched_jd_skills.append(jd_skill)
        remaining_jds.remove(jd_skill)
        for i, c in enumerate(available_candidates):
            if c.skill_name == cand_skill_name:
                available_candidates.pop(i)
                break

    # Tier 1: Exact Match
    for jd in list(remaining_jds):
        norm_jd = normalize_skill(jd.skill_name)
        if not norm_jd:
            continue
        for c in available_candidates:
            if normalize_skill(c.skill_name) == norm_jd:
                _consume_match(c.skill_name, jd, "exact", 1.0)
                break

    # Tier 2: Alias Match
    for jd in list(remaining_jds):
        alias_jd = resolve_alias(jd.skill_name)
        norm_jd = normalize_skill(jd.skill_name)
        if not alias_jd:
            continue
        for c in available_candidates:
            norm_c = normalize_skill(c.skill_name)
            if norm_c != norm_jd and resolve_alias(c.skill_name) == alias_jd:
                _consume_match(c.skill_name, jd, "alias", 0.95)
                break

    # Tier 3: Fuzzy Match
    for jd in list(remaining_jds):
        norm_jd = normalize_skill(jd.skill_name)
        if not norm_jd:
            continue
        best_score = -1.0
        best_cand: Skill | None = None
        for c in available_candidates:
            norm_c = normalize_skill(c.skill_name)
            score = float(fuzz.token_set_ratio(norm_jd, norm_c))
            if score > best_score:
                best_score = score
                best_cand = c

        if best_score >= fuzzy_threshold and best_cand is not None:
            sim = min(1.0, max(0.0, round(best_score / 100.0, 2)))
            _consume_match(best_cand.skill_name, jd, "fuzzy", sim)

    # Tier 4: Semantic Matching via LLM (leftovers only)
    if use_llm and remaining_jds and available_candidates:
        semantic_matches = adjudicate_semantic_matches(
            unmatched_jds=remaining_jds,
            available_cands=available_candidates,
            threshold=semantic_threshold,
            use_cache=use_cache,
        )

        for sm in semantic_matches:
            # Map back to real JD and candidate Skill objects using normalized comparison
            norm_target_jd = normalize_skill(sm.jd_skill)
            norm_target_cand = normalize_skill(sm.candidate_skill)

            target_jd = next((j for j in remaining_jds if normalize_skill(j.skill_name) == norm_target_jd), None)
            target_cand = next((c for c in available_candidates if normalize_skill(c.skill_name) == norm_target_cand), None)

            if target_jd and target_cand:
                sim = min(1.0, max(0.0, round(sm.similarity, 2)))
                _consume_match(target_cand.skill_name, target_jd, "semantic", sim)

    # Score calculation
    score = calculate_match_score(matched_jd_skills, job_skills)

    # Missing skills identification
    missing_skills = prioritize_missing_skills(remaining_jds)

    return matched_skills, missing_skills, score


def match_skills_deterministic(
    candidate_skills: Sequence[Skill],
    job_skills: Sequence[Skill],
    fuzzy_threshold: int = FUZZY_THRESHOLD,
) -> tuple[list[MatchedSkill], list[MissingSkill], int]:
    """Execute purely deterministic matching (Tiers 1-3). Maintained for backwards compatibility."""
    return match_skills_pipeline(
        candidate_skills=candidate_skills,
        job_skills=job_skills,
        fuzzy_threshold=fuzzy_threshold,
        use_llm=False,
    )


def build_skill_match_result(
    candidate_id: str,
    jd_source_file: str,
    candidate_skills: Sequence[Skill],
    job_skills: Sequence[Skill],
    fuzzy_threshold: int = FUZZY_THRESHOLD,
    semantic_threshold: float = SEMANTIC_THRESHOLD,
    use_llm: bool = True,
    use_cache: bool = True,
) -> SkillMatchResult:
    """Build a validated SkillMatchResult instance from the 4-tier matching pipeline."""
    matched, missing, score = match_skills_pipeline(
        candidate_skills=candidate_skills,
        job_skills=job_skills,
        fuzzy_threshold=fuzzy_threshold,
        semantic_threshold=semantic_threshold,
        use_llm=use_llm,
        use_cache=use_cache,
    )
    return SkillMatchResult(
        candidate_id=candidate_id,
        jd_source_file=jd_source_file,
        match_score=score,
        matched_skills=matched,
        missing_skills=missing,
    )
