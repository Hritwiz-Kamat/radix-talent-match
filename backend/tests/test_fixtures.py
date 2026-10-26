from app.core import storage
from app.schemas import CandidateProfile


def test_four_fixture_profiles_load():
    keys = storage.list_keys("profiles")
    assert len(keys) >= 4
    for k in keys:
        print("PROFILE KEY:", k)
        print("PROFILE DATA:", storage.load("profiles", k))
        CandidateProfile(**storage.load("profiles", k))
