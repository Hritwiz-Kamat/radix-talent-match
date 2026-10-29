"""Unit, integration, and API tests for Role 5 (Skill Matching)."""
import json
import pytest
from fastapi.testclient import TestClient

from app.core import storage
from app.main import app
from app.schemas import (
    CATEGORY_CODES,
    CandidateProfile,
    ExtractedSkillList,
    MatchedSkill,
    MissingSkill,
    Skill,
    SkillMatchResult,
)
from app.skill_matching.matching import (
    ALIASES,
    SemanticMatchItem,
    SemanticMatchOutput,
    adjudicate_semantic_matches,
    alias_match,
    build_skill_match_result,
    calculate_match_score,
    exact_match,
    fuzzy_match,
    match_skills_deterministic,
    match_skills_pipeline,
    normalize_skill,
    parse_json_reply,
    prioritize_missing_skills,
    resolve_alias,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def setup_test_jd():
    """Save a clean test JD into storage (kind 'jd') for testing real endpoints."""
    jd = ExtractedSkillList(
        source_type="jd",
        source_file="google-swe-test.pdf",
        company="Google LLC",
        role="Software Engineer",
        skills=[
            Skill(skill_name="Python", category_code="COD", evidence="ev", confidence="high", importance="required"),
            Skill(skill_name="C++", category_code="COD", evidence="ev", confidence="high", importance="required"),
            Skill(skill_name="Kubernetes", category_code="CLOUD", evidence="ev", confidence="high", importance="preferred"),
        ],
    )
    storage.save("jd", "google-swe-test.pdf", jd)
    yield jd
    (storage.ROOT / "jd" / "google-swe-test.pdf.json").unlink(missing_ok=True)
    (storage.ROOT / "results" / "match-ananya-rao-google-swe-test.pdf.json").unlink(missing_ok=True)


# ============================================================================
# 1. Normalization & Alias Tests
# ============================================================================

def test_normalize_skill_cases():
    """Verify lowercasing, whitespace trimming, and punctuation handling."""
    assert normalize_skill("  Python  ") == "python"
    assert normalize_skill("Node.js") == "nodejs"
    assert normalize_skill("React.JS") == "reactjs"
    assert normalize_skill("C++") == "c++"
    assert normalize_skill("C#") == "c#"
    assert normalize_skill("PostgreSQL (RDBMS)") == "postgresql rdbms"
    assert normalize_skill("CI/CD - Pipelines") == "ci cd pipelines"
    assert normalize_skill("") == ""


def test_resolve_alias():
    """Verify canonical alias mapping."""
    assert resolve_alias("js") == "javascript"
    assert resolve_alias("JS") == "javascript"
    assert resolve_alias("postgres") == "postgresql"
    assert resolve_alias("ML") == "machine learning"
    assert resolve_alias("K8s") == "kubernetes"
    assert resolve_alias("Docker") == "docker"


# ============================================================================
# 2. Matching Tiers Unit Tests
# ============================================================================

def test_exact_match_success():
    """Exact match should find identical normalized names with similarity 1.0."""
    cand = ["Python", "Node.js", "Docker"]
    jd = ["python", "nodejs", "Kubernetes"]

    matches = exact_match(cand, jd)
    assert len(matches) == 2
    assert matches[0].jd_skill == "python"
    assert matches[0].candidate_skill == "Python"
    assert matches[0].match_type == "exact"
    assert matches[0].similarity == 1.0


def test_alias_match_success():
    """Alias match resolves common acronyms with similarity 0.95."""
    cand = ["JS", "Postgres", "ML"]
    jd = ["JavaScript", "PostgreSQL", "Machine Learning"]

    matches = alias_match(cand, jd)
    assert len(matches) == 3
    for m in matches:
        assert m.match_type == "alias"
        assert m.similarity == 0.95


def test_alias_match_does_not_label_exact_match():
    """If normalized skills are already identical, alias_match must not match them."""
    cand = ["JavaScript"]
    jd = ["JavaScript"]
    matches = alias_match(cand, jd)
    assert len(matches) == 0


def test_fuzzy_match_above_threshold():
    """Fuzzy match with RapidFuzz token_set_ratio >= 88."""
    cand = ["Docker Containers", "Apache Kafka Streaming"]
    jd = ["Docker Container", "Kafka"]

    matches = fuzzy_match(cand, jd, threshold=88)
    assert len(matches) >= 1
    assert matches[0].jd_skill == "Docker Container"
    assert matches[0].candidate_skill == "Docker Containers"
    assert matches[0].match_type == "fuzzy"
    assert 0.88 <= matches[0].similarity <= 1.0


def test_fuzzy_match_below_threshold():
    """Fuzzy match should reject dissimilar skill pairs below threshold."""
    cand = ["Python Programming"]
    jd = ["Java Programming"]
    matches = fuzzy_match(cand, jd, threshold=88)
    assert len(matches) == 0


def test_candidate_skill_not_reused():
    """A single candidate skill should not be consumed by multiple JD skills."""
    cand_skills = [
        Skill(skill_name="Python", category_code="COD", evidence="ev", confidence="high"),
    ]
    jd_skills = [
        Skill(skill_name="Python", category_code="COD", evidence="ev", confidence="high", importance="required"),
        Skill(skill_name="Python Scripting", category_code="COD", evidence="ev", confidence="high", importance="preferred"),
    ]

    matched, missing, score = match_skills_deterministic(cand_skills, jd_skills)
    assert len(matched) == 1
    assert len(missing) == 1
    assert matched[0].jd_skill == "Python"
    assert missing[0].skill_name == "Python Scripting"


# ============================================================================
# 3. Score Calculation Tests
# ============================================================================

def test_calculate_match_score_all_matched():
    """All skills matched should yield 100."""
    skills = [
        Skill(skill_name="Python", category_code="COD", evidence="ev", confidence="high", importance="required"),
        Skill(skill_name="SQL", category_code="SQL", evidence="ev", confidence="high", importance="preferred"),
    ]
    assert calculate_match_score(skills, skills) == 100


def test_calculate_match_score_none_matched():
    """No skills matched should yield 0."""
    skills = [
        Skill(skill_name="Python", category_code="COD", evidence="ev", confidence="high", importance="required"),
    ]
    assert calculate_match_score([], skills) == 0


def test_calculate_match_score_empty_jd():
    """Empty JD skill list should safely return 0 without division by zero."""
    assert calculate_match_score([], []) == 0


def test_calculate_match_score_worked_example():
    """Worked example: 2 required (weight 2 each) + 2 preferred (weight 1 each) -> 5/6 = 83%."""
    r1 = Skill(skill_name="R1", category_code="COD", evidence="ev", confidence="high", importance="required")
    r2 = Skill(skill_name="R2", category_code="DSA", evidence="ev", confidence="high", importance="required")
    p1 = Skill(skill_name="P1", category_code="CLOUD", evidence="ev", confidence="high", importance="preferred")
    p2 = Skill(skill_name="P2", category_code="SQL", evidence="ev", confidence="high", importance="preferred")

    all_jds = [r1, r2, p1, p2]
    matched_jds = [r1, r2, p1]

    score = calculate_match_score(matched_jds, all_jds)
    assert score == 83


def test_calculate_match_score_unspecified_importance():
    """Unspecified importance (None) should default to weight 1."""
    s1 = Skill(skill_name="S1", category_code="COD", evidence="ev", confidence="high", importance=None)
    s2 = Skill(skill_name="S2", category_code="SQL", evidence="ev", confidence="high", importance=None)
    assert calculate_match_score([s1], [s1, s2]) == 50


# ============================================================================
# 4. Missing Skills Prioritization & Suggestions Tests
# ============================================================================

def test_missing_skills_prioritization_and_suggestions():
    """Missing skills must be ordered by required first, category code, and name."""
    u1 = Skill(skill_name="SQL Querying", category_code="SQL", evidence="ev", confidence="high", importance="preferred")
    u2 = Skill(skill_name="Algorithms", category_code="DSA", evidence="ev", confidence="high", importance="required")
    u3 = Skill(skill_name="Docker", category_code="CLOUD", evidence="ev", confidence="high", importance="required")
    u4 = Skill(skill_name="Bash Scripting", category_code="OS", evidence="ev", confidence="high", importance=None)

    missing = prioritize_missing_skills([u1, u2, u3, u4])

    assert len(missing) == 4
    assert missing[0].skill_name == "Algorithms"
    assert missing[0].importance == "required"
    assert missing[0].category_code == "DSA"

    assert missing[1].skill_name == "Docker"
    assert missing[1].importance == "required"
    assert missing[1].category_code == "CLOUD"

    assert missing[2].skill_name == "SQL Querying"
    assert missing[2].importance == "preferred"

    assert missing[3].skill_name == "Bash Scripting"
    assert missing[3].importance is None

    for m in missing:
        assert f"using {m.skill_name}" in m.suggestion


# ============================================================================
# 5. LLM Semantic Matching, Caching, and Fallback Tests
# ============================================================================

def test_parse_json_reply_handles_fences_and_chatter():
    """parse_json_reply strips markdown fences and grabs the JSON block."""
    raw = "Here is the response:\n```json\n{\"matches\": []}\n```\nHope it helps!"
    parsed = parse_json_reply(raw)
    assert parsed == {"matches": []}


def test_semantic_match_above_threshold(monkeypatch, tmp_path):
    """Semantic match above 0.70 threshold is accepted."""
    monkeypatch.setattr("app.skill_matching.matching.CACHE_DIR", tmp_path)

    reply = json.dumps({
        "matches": [
            {"jd_skill": "Cloud Compute VMs", "candidate_skill": "Amazon EC2", "similarity": 0.88, "reason": "Equivalent"}
        ]
    })
    monkeypatch.setattr("app.core.llm.ask", lambda msgs: reply)

    jd_skills = [Skill(skill_name="Cloud Compute VMs", category_code="CLOUD", evidence="ev", confidence="high", importance="required")]
    cand_skills = [Skill(skill_name="Amazon EC2", category_code="CLOUD", evidence="ev", confidence="high")]

    matched, missing, score = match_skills_pipeline(cand_skills, jd_skills, use_llm=True, use_cache=True)
    assert len(matched) == 1
    assert matched[0].match_type == "semantic"
    assert matched[0].candidate_skill == "Amazon EC2"
    assert matched[0].jd_skill == "Cloud Compute VMs"
    assert matched[0].similarity == 0.88
    assert len(missing) == 0
    assert score == 100


def test_semantic_match_below_threshold_rejected(monkeypatch, tmp_path):
    """Semantic match with similarity < 0.70 is rejected and skill remains missing."""
    monkeypatch.setattr("app.skill_matching.matching.CACHE_DIR", tmp_path)

    reply = json.dumps({
        "matches": [
            {"jd_skill": "Machine Learning", "candidate_skill": "scikit-learn", "similarity": 0.65}
        ]
    })
    monkeypatch.setattr("app.core.llm.ask", lambda msgs: reply)

    jd_skills = [Skill(skill_name="Machine Learning", category_code="AI", evidence="ev", confidence="high", importance="required")]
    cand_skills = [Skill(skill_name="scikit-learn", category_code="AI", evidence="ev", confidence="high")]

    matched, missing, score = match_skills_pipeline(cand_skills, jd_skills, use_llm=True, use_cache=True)
    assert len(matched) == 0
    assert len(missing) == 1
    assert missing[0].skill_name == "Machine Learning"
    assert score == 0


def test_semantic_match_llm_failure_fallback(monkeypatch, tmp_path):
    """When LLM raises an error, deterministic matches are preserved and remaining become missing."""
    monkeypatch.setattr("app.skill_matching.matching.CACHE_DIR", tmp_path)

    def fail_ask(msgs):
        raise RuntimeError("All OpenRouter models failed: 429 Too Many Requests")

    monkeypatch.setattr("app.core.llm.ask", fail_ask)

    jd_skills = [
        Skill(skill_name="Python", category_code="COD", evidence="ev", confidence="high", importance="required"),
        Skill(skill_name="Microservices Architecture", category_code="SYSD", evidence="ev", confidence="high", importance="preferred"),
    ]
    cand_skills = [
        Skill(skill_name="python", category_code="COD", evidence="ev", confidence="high"),
        Skill(skill_name="Distributed Systems", category_code="SYSD", evidence="ev", confidence="high"),
    ]

    matched, missing, score = match_skills_pipeline(cand_skills, jd_skills, use_llm=True, use_cache=True)
    assert len(matched) == 1
    assert matched[0].jd_skill == "Python"
    assert matched[0].match_type == "exact"
    assert len(missing) == 1
    assert missing[0].skill_name == "Microservices Architecture"
    assert score == 67


def test_semantic_caching_hit_and_miss(monkeypatch, tmp_path):
    """First call writes to disk cache; second call reads from cache without calling LLM."""
    monkeypatch.setattr("app.skill_matching.matching.CACHE_DIR", tmp_path)

    call_count = 0

    def mock_ask(msgs):
        nonlocal call_count
        call_count += 1
        return json.dumps({
            "matches": [
                {"jd_skill": "Cloud VMs", "candidate_skill": "EC2", "similarity": 0.85}
            ]
        })

    monkeypatch.setattr("app.core.llm.ask", mock_ask)

    jd_skills = [Skill(skill_name="Cloud VMs", category_code="CLOUD", evidence="ev", confidence="high")]
    cand_skills = [Skill(skill_name="EC2", category_code="CLOUD", evidence="ev", confidence="high")]

    matched1, _, _ = match_skills_pipeline(cand_skills, jd_skills, use_llm=True, use_cache=True)
    assert call_count == 1
    matched2, _, _ = match_skills_pipeline(cand_skills, jd_skills, use_llm=True, use_cache=True)
    assert call_count == 1
    assert matched2[0].similarity == 0.85


# ============================================================================
# 6. Phase 5: Storage Integration & Matrix Endpoint Tests
# ============================================================================

def test_api_skill_match_real_storage_success(client, setup_test_jd, monkeypatch):
    """
    Integration test: POST /api/skill-match loads real candidate (ananya-rao)
    and stored JD, calculates matches, persists result to storage, and returns 200.
    """
    # Mock LLM in case Tier 4 is invoked for leftovers
    monkeypatch.setattr("app.core.llm.ask", lambda msgs: '{"matches": []}')

    payload = {
        "candidate_id": "ananya-rao",
        "jd_source_file": "google-swe-test.pdf",
    }
    res = client.post("/api/skill-match", json=payload)
    assert res.status_code == 200

    data = res.json()
    validated = SkillMatchResult(**data)
    assert validated.candidate_id == "ananya-rao"
    assert validated.jd_source_file == "google-swe-test.pdf"
    assert validated.match_score > 0

    # Verify result was saved to storage kind 'results'
    saved = storage.load("results", "match-ananya-rao-google-swe-test.pdf")
    assert saved is not None
    assert saved["candidate_id"] == "ananya-rao"
    assert saved["match_score"] == validated.match_score


def test_api_skill_match_missing_candidate_returns_404(client, setup_test_jd):
    """Missing candidate profile returns 404 Not Found."""
    payload = {
        "candidate_id": "ghost-candidate-999",
        "jd_source_file": "google-swe-test.pdf",
    }
    res = client.post("/api/skill-match", json=payload)
    assert res.status_code == 404
    assert "ghost-candidate-999" in res.json()["detail"]


def test_api_skill_match_missing_jd_returns_404(client):
    """Missing job description returns 404 Not Found."""
    payload = {
        "candidate_id": "ananya-rao",
        "jd_source_file": "nonexistent-jd-file.pdf",
    }
    res = client.post("/api/skill-match", json=payload)
    assert res.status_code == 404
    assert "nonexistent-jd-file.pdf" in res.json()["detail"]


def test_api_skill_match_invalid_candidate_returns_422(client, monkeypatch):
    """Corrupt or invalid candidate profile in storage triggers 422 Unprocessable Entity."""
    # Mock storage.load to return invalid candidate structure
    monkeypatch.setattr(storage, "load", lambda kind, key: {"candidate_id": "bad", "skills": "not-a-list"})

    payload = {
        "candidate_id": "bad-cand",
        "jd_source_file": "any-jd.pdf",
    }
    res = client.post("/api/skill-match", json=payload)
    assert res.status_code == 422


def test_api_skill_match_mock_flag_fallback(client):
    """When mock: true is passed, endpoint returns MOCK_MATCH adapted to inputs."""
    payload = {
        "candidate_id": "any-mock-id",
        "jd_source_file": "any-mock-jd.pdf",
        "mock": True,
    }
    res = client.post("/api/skill-match", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["candidate_id"] == "any-mock-id"
    assert data["jd_source_file"] == "any-mock-jd.pdf"


def test_api_matrix_endpoint_returns_saved_results(client, setup_test_jd, monkeypatch):
    """GET /api/skill-match/matrix reads saved results and returns them dynamically."""
    monkeypatch.setattr("app.core.llm.ask", lambda msgs: '{"matches": []}')

    # Execute a match first so a result is saved
    client.post(
        "/api/skill-match",
        json={"candidate_id": "ananya-rao", "jd_source_file": "google-swe-test.pdf"},
    )

    res = client.get("/api/skill-match/matrix")
    assert res.status_code == 200
    data = res.json()
    assert "matrix" in data
    assert isinstance(data["matrix"], list)
    assert len(data["matrix"]) >= 1

    # Check entry fields
    entry = next(
        (m for m in data["matrix"] if m["candidate_id"] == "ananya-rao" and m["jd_source_file"] == "google-swe-test.pdf"),
        None,
    )
    assert entry is not None
    assert "match_score" in entry
    assert isinstance(entry["match_score"], int)


def test_api_matrix_endpoint_excludes_unrelated_results(client, monkeypatch):
    """GET /api/skill-match/matrix ignores results that do not start with 'match-'."""
    # Mock storage.list_keys to include an unrelated key
    monkeypatch.setattr(storage, "list_keys", lambda kind: ["talent-check-company-1", "match-cand-jd"])
    monkeypatch.setattr(
        storage,
        "load",
        lambda kind, key: {"candidate_id": "cand", "jd_source_file": "jd", "match_score": 75} if key == "match-cand-jd" else None,
    )

    res = client.get("/api/skill-match/matrix")
    assert res.status_code == 200
    matrix = res.json()["matrix"]
    assert len(matrix) == 1
    assert matrix[0]["candidate_id"] == "cand"


def test_skill_match_endpoint_bad_input(client):
    """Bad-input path: missing required fields in request body returns 422 Unprocessable Entity."""
    res = client.post("/api/skill-match", json={})
    assert res.status_code == 422

    res_partial = client.post("/api/skill-match", json={"candidate_id": "ananya-rao"})
    assert res_partial.status_code == 422
