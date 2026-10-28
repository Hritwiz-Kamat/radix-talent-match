"""
THE SHARED DATA CONTRACT  --  v1.0 (PROPOSED, lock it on Day 1)

Rules:
  * This file is the single source of truth. Every role imports from here.
  * Nobody edits it alone. Changes go through the Scrum Master, get a version bump
    below, and are announced in the team chat the same hour.
  * Changes vs the brief are marked  # CHANGED  /  # ADDED  so the team can debate them.

Changelog:
  v1.0  initial lock
  v1.1  SkillsetGap: added company_aggregate_level and role_weight (Optional, additive, Role 4 only)
  v1.2  TalentCheckResult: added data_source (Optional[str]; values: supabase|json|csv|placeholder)
"""
from __future__ import annotations

from typing import Literal, Optional, get_args

from pydantic import BaseModel, Field, field_validator

CONTRACT_VERSION = "1.2"

CategoryCode = Literal[
    "DSA", "COD", "OOD", "APTI", "COMM", "AI",
    "CLOUD", "SQL", "SWE", "SYSD", "NETW", "OS", "OTHER",
]
CATEGORY_CODES: list[str] = list(get_args(CategoryCode))
TWELVE_SKILLSETS: list[str] = [c for c in CATEGORY_CODES if c != "OTHER"]

CATEGORY_HELP = {
    "COD": "Coding / programming languages and general coding ability (Python, Java, C++)",
    "DSA": "Data Structures & Algorithms, problem solving, complexity",
    "OOD": "Object-Oriented Design, design patterns, SOLID",
    "APTI": "Aptitude: quantitative, logical, analytical reasoning",
    "COMM": "Communication: written/verbal, stakeholder, teamwork, presentation",
    "AI": "AI/ML/Data science: ML, deep learning, statistics, NLP, LLMs, data analysis",
    "CLOUD": "Cloud & DevOps: AWS/Azure/GCP, Docker, Kubernetes, CI/CD",
    "SQL": "Databases and SQL, query writing, data modelling",
    "SWE": "Software engineering practice: SDLC, testing, Git, agile, APIs, debugging",
    "SYSD": "System design: scalability, distributed systems, architecture",
    "NETW": "Networking: TCP/IP, HTTP, DNS, protocols",
    "OS": "Operating systems: processes, memory, Linux, concurrency",
    "OTHER": "Anything that fits none of the twelve above",
}

Confidence = Literal["high", "medium", "low"]
Importance = Literal["required", "preferred"]


class Skill(BaseModel):
    skill_name: str = Field(min_length=1)
    category_code: CategoryCode
    evidence: str = Field(min_length=1, description="short quote or reason")
    confidence: Confidence
    # ADDED: only meaningful for JDs. Lets Skill Matching rank the gap list.
    importance: Optional[Importance] = None

    @field_validator("skill_name", "evidence")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class ExtractedSkillList(BaseModel):
    """Output of Role 1 (JD Analytics) and Role 2 (Resume Parsing)."""
    source_type: Literal["jd", "resume"]
    source_file: str
    company: Optional[str] = None
    role: Optional[str] = None
    skills: list[Skill]
    # ADDED: resume extras (education, projects, experience). Free-form on purpose.
    extras: dict = Field(default_factory=dict)


class ProfileItem(BaseModel):
    """Generic entry for hackathons / internships / certifications."""
    title: str
    organization: Optional[str] = None
    description: Optional[str] = None
    year: Optional[str] = None


class CandidateProfile(BaseModel):
    """Output of Role 3 (Profile Builder). Input to Roles 4 and 5."""
    candidate_id: str = Field(description="slug, e.g. 'anny-roy'. Primary key everywhere.")  # ADDED
    name: str
    email: Optional[str] = None
    education: Optional[str] = None
    skills: list[Skill] = Field(default_factory=list)
    hackathons: list[ProfileItem] = Field(default_factory=list)
    internships: list[ProfileItem] = Field(default_factory=list)
    certifications: list[ProfileItem] = Field(default_factory=list)
    preferred_roles: list[str] = Field(default_factory=list)
    cv_file: Optional[str] = None


class SkillsetGap(BaseModel):
    category_code: CategoryCode
    required_level: int = Field(ge=0, le=10)
    candidate_level: int = Field(ge=0, le=10)   # CHANGED: 0 allowed = "no evidence at all"
    gap: bool
    gap_size: int = Field(default=0, ge=0, le=10)                 # ADDED
    explanation: Optional[str] = None                             # ADDED: why this level
    # ADDED v1.1 (Role 4 only, additive — contract fields above are unchanged)
    company_aggregate_level: Optional[int] = None  # raw CSV value before role weighting
    role_weight: Optional[float] = None            # fraction applied to aggregate -> required_level


class TalentCheckResult(BaseModel):
    """Output of Role 4."""
    company: str
    candidate_id: str                                             # ADDED
    skillset_gap: list[SkillsetGap]
    readiness_score: int = Field(ge=0, le=100)
    scoring_method: Optional[str] = None                          # ADDED: one-line formula, shown in UI
    # ADDED v1.2 (Role 4 only, additive) — "supabase"|"json"|"csv"|"placeholder"
    data_source: Optional[str] = None



class MatchedSkill(BaseModel):
    jd_skill: str
    candidate_skill: str
    match_type: Literal["exact", "alias", "fuzzy", "semantic"]
    similarity: float = Field(ge=0, le=1)


class MissingSkill(BaseModel):
    skill_name: str
    category_code: CategoryCode
    importance: Optional[Importance] = None
    suggestion: Optional[str] = None                              # ADDED: "what to learn"


class SkillMatchResult(BaseModel):
    """Output of Role 5."""
    jd_source_file: str
    candidate_id: str                                             # ADDED
    match_score: int = Field(ge=0, le=100)
    matched_skills: list[MatchedSkill]
    missing_skills: list[MissingSkill]
