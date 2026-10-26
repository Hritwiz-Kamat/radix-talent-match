"""Tests the Supabase adapter against a FAKE Supabase (no network)."""
import httpx
import pytest
from app.core import storage

DB = {}


def fake_supabase(request: httpx.Request) -> httpx.Response:
    if request.method == "POST" and "/rest/v1/documents" in request.url.path:
        import json
        body = json.loads(request.content)
        DB[(body["kind"], body["key"])] = body["data"]
        return httpx.Response(201)
    if request.method == "GET" and "/rest/v1/documents" in request.url.path:
        q = dict(request.url.params)
        if "key" in q and q["key"].startswith("eq."):
            row = DB.get((q["kind"][3:], q["key"][3:]))
            return httpx.Response(200, json=[{"data": row}] if row else [])
        return httpx.Response(200, json=[{"key": k} for (kind, k) in DB if kind == q["kind"][3:]])
    return httpx.Response(404)


@pytest.fixture(autouse=True)
def fake(monkeypatch, tmp_path):
    DB.clear()
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "k")
    monkeypatch.setenv("STORAGE_BACKEND", "supabase")
    monkeypatch.setattr(storage, "ROOT", tmp_path)
    monkeypatch.setattr(storage, "_client", lambda: httpx.Client(transport=httpx.MockTransport(fake_supabase)))


def test_save_writes_to_supabase_and_mirror(tmp_path):
    storage.save("profiles", "Test Person", {"name": "T"})
    assert DB[("profiles", "test-person")] == {"name": "T"}
    assert (tmp_path / "profiles" / "test-person.json").exists()
    assert storage.load("profiles", "test-person") == {"name": "T"}
    assert storage.load_with_source("profiles", "test-person") == ({"name": "T"}, "supabase")
    assert "test-person" in storage.list_keys("profiles")


def test_falls_back_to_local_when_supabase_down(monkeypatch):
    storage.save("profiles", "a", {"v": 1})
    def boom(_): raise httpx.ConnectError("down")
    monkeypatch.setattr(storage, "_client", lambda: httpx.Client(transport=httpx.MockTransport(boom)))
    assert storage.load("profiles", "a") == {"v": 1}      # served from the local mirror
    assert storage.load_with_source("profiles", "a") == ({"v": 1}, "json")


def test_strict_mode_raises(monkeypatch):
    def boom(_): raise httpx.ConnectError("down")
    monkeypatch.setattr(storage, "_client", lambda: httpx.Client(transport=httpx.MockTransport(boom)))
    monkeypatch.setenv("STORAGE_STRICT", "1")
    with pytest.raises(RuntimeError):
        storage.save("profiles", "b", {"v": 2})
