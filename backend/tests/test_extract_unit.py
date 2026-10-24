import pytest
from app.core.extract import parse_json_reply, _LLMOut, _gate


def test_parse_handles_fences_and_chatter():
    reply = 'Sure!\n```json\n{"skills":[{"skill_name":"SQL","category_code":"SQL","evidence":"x","confidence":"high","importance":null}]}\n```'
    out = _LLMOut(**parse_json_reply(reply))
    assert out.skills[0].skill_name == "SQL"


def test_bad_category_is_rejected():
    with pytest.raises(Exception):
        _LLMOut(**{"skills": [{"skill_name": "x", "category_code": "MAGIC", "evidence": "e", "confidence": "high"}]})


def test_gate_flags_too_few():
    assert _gate([])
