from app.core import storage
from app.schemas import CandidateProfile


def test_four_fixture_profiles_load():
    keys = storage.list_keys("profiles")
    assert len(keys) >= 4
    for k in keys:
        CandidateProfile(**storage.load("profiles", k))
