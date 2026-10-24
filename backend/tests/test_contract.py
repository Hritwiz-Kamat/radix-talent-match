from app import mocks
from app.schemas import ExtractedSkillList, SkillMatchResult, TalentCheckResult, CandidateProfile


def test_mocks_roundtrip():
    for model, obj in [(ExtractedSkillList, mocks.MOCK_JD), (CandidateProfile, mocks.MOCK_PROFILE),
                       (TalentCheckResult, mocks.MOCK_TALENT_CHECK), (SkillMatchResult, mocks.MOCK_MATCH)]:
        assert model(**obj.model_dump(mode="json"))
