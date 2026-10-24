"""Valid fake data for every contract object. Use these on Day 1 so nobody is blocked."""
from .schemas import *

MOCK_SKILLS = [
    Skill(skill_name="Python", category_code="COD", evidence="3+ years of Python", confidence="high", importance="required"),
    Skill(skill_name="Data Structures", category_code="DSA", evidence="strong DSA fundamentals", confidence="high", importance="required"),
    Skill(skill_name="SQL", category_code="SQL", evidence="write complex queries", confidence="medium", importance="preferred"),
    Skill(skill_name="Docker", category_code="CLOUD", evidence="containerised services", confidence="low", importance="preferred"),
]

MOCK_JD = ExtractedSkillList(source_type="jd", source_file="mock_google_swe.pdf", company="Google LLC",
                             role="Software Engineer", skills=MOCK_SKILLS)
MOCK_RESUME = ExtractedSkillList(source_type="resume", source_file="mock_anny.pdf", skills=MOCK_SKILLS[:3],
                                 extras={"education": "B.Tech CSE", "projects": [], "experience": []})
MOCK_PROFILE = CandidateProfile(candidate_id="mock-candidate", name="Mock Candidate", email="mock@example.com",
                                education="B.Tech CSE", skills=MOCK_SKILLS[:3], preferred_roles=["Software Engineer"])
MOCK_TALENT_CHECK = TalentCheckResult(
    company="Google LLC", candidate_id="mock-candidate", readiness_score=62,
    skillset_gap=[SkillsetGap(category_code="DSA", required_level=8, candidate_level=6, gap=True, gap_size=2),
                  SkillsetGap(category_code="SQL", required_level=5, candidate_level=6, gap=False)])
MOCK_MATCH = SkillMatchResult(
    jd_source_file="mock_google_swe.pdf", candidate_id="mock-candidate", match_score=71,
    matched_skills=[MatchedSkill(jd_skill="Python", candidate_skill="Python", match_type="exact", similarity=1.0)],
    missing_skills=[MissingSkill(skill_name="Docker", category_code="CLOUD", importance="preferred",
                                 suggestion="Containerise one of your projects")])
