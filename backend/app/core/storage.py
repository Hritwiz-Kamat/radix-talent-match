"""
Storage layer. SUPABASE IS THE PRIMARY STORE (hackathon requirement); a local JSON mirror is the safety net.

Every module uses only these functions, so nobody writes SQL or HTTP calls:
    save(kind, key, obj)      load(kind, key)      list_keys(kind)      upload_file(...)

kinds in use: profiles | jd | resume | results | company_skillsets

How it works
  * save : writes to Supabase (table `documents`, JSONB) AND to data/store/ (local mirror).
  * load : reads Supabase first; if Supabase is unreachable or has no row, falls back to the local mirror.
  * Set STORAGE_BACKEND=local in .env to work offline on your own laptop (no Supabase calls at all).
  * Set STORAGE_STRICT=1 to make a failed Supabase write raise an error instead of just warning.
The backend uses the SERVICE ROLE key. It must NEVER reach the frontend or git.
"""
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx

log = logging.getLogger("storage")
ROOT = Path(__file__).resolve().parents[2] / "data" / "store"
TABLE = "documents"
BUCKET = "candidate-files"


# ---------- config helpers ----------
def _url() -> str:
    return os.getenv("SUPABASE_URL", "").rstrip("/")


def supabase_enabled() -> bool:
    if os.getenv("STORAGE_BACKEND", "supabase").lower() == "local":
        return False
    return bool(_url() and os.getenv("SUPABASE_SERVICE_KEY"))


def _client() -> httpx.Client:           # tests replace this with a mock transport
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    return httpx.Client(timeout=8, headers={"apikey": key, "Authorization": f"Bearer {key}"})


def _slug(key: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", key).strip("-").lower()


def _fail(msg: str, err: Exception | None = None):
    if os.getenv("STORAGE_STRICT") == "1" and err is not None:
        raise RuntimeError(f"Supabase: {msg}") from err
    log.warning("Supabase: %s (%s) -> using local mirror", msg, err)


# ---------- JSON documents ----------
def save(kind: str, key: str, obj) -> None:
    data = obj.model_dump(mode="json") if hasattr(obj, "model_dump") else obj
    key = _slug(key)
    p = ROOT / kind
    p.mkdir(parents=True, exist_ok=True)                       # local mirror (always)
    (p / f"{key}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    if supabase_enabled():
        try:
            with _client() as c:
                r = c.post(f"{_url()}/rest/v1/{TABLE}?on_conflict=kind,key",
                           headers={"Prefer": "resolution=merge-duplicates,return=minimal",
                                    "Content-Type": "application/json"},
                           json={"kind": kind, "key": key, "data": data,
                                 "updated_at": datetime.now(timezone.utc).isoformat()})
                r.raise_for_status()
        except Exception as e:
            _fail(f"save {kind}/{key} failed", e)


def load_with_source(kind: str, key: str) -> tuple[object | None, str | None]:
    """Load a document and report whether it came from Supabase or the local JSON mirror."""
    key = _slug(key)
    if supabase_enabled():
        try:
            with _client() as c:
                r = c.get(f"{_url()}/rest/v1/{TABLE}",
                          params={"kind": f"eq.{kind}", "key": f"eq.{key}", "select": "data"})
                r.raise_for_status()
                rows = r.json()
                if rows:
                    return rows[0]["data"], "supabase"
        except Exception as e:
            _fail(f"load {kind}/{key} failed", e)
    f = ROOT / kind / f"{key}.json"
    if not f.exists() and not key.endswith(".pdf"):
        f_alt = ROOT / kind / f"{key}.pdf.json"
        if f_alt.exists():
            f = f_alt
    return (json.loads(f.read_text(encoding="utf-8")), "json") if f.exists() else (None, None)


def load(kind: str, key: str):
    return load_with_source(kind, key)[0]


def list_keys(kind: str) -> list[str]:
    keys = set()
    p = ROOT / kind
    if p.exists():
        keys |= {f.stem for f in p.glob("*.json")}
    if supabase_enabled():
        try:
            with _client() as c:
                r = c.get(f"{_url()}/rest/v1/{TABLE}", params={"kind": f"eq.{kind}", "select": "key"})
                r.raise_for_status()
                keys |= {row["key"] for row in r.json()}
        except Exception as e:
            _fail(f"list {kind} failed", e)
    return sorted(keys)


# ---------- files (CVs, uploaded JDs/resumes) ----------
def upload_file(path: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Stores a file in the Supabase Storage bucket `candidate-files` (+ local copy). Returns the object path."""
    safe = "/".join(_slug(part) if i < path.count("/") else re.sub(r"[^\w.\- ]+", "_", part)
                    for i, part in enumerate(path.split("/")))
    local = ROOT / "files" / safe
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_bytes(data)
    if supabase_enabled():
        try:
            with _client() as c:
                r = c.post(f"{_url()}/storage/v1/object/{BUCKET}/{safe}",
                           headers={"Content-Type": content_type, "x-upsert": "true"}, content=data)
                r.raise_for_status()
        except Exception as e:
            _fail(f"upload {safe} failed", e)
    return safe


# ---------- ops helpers ----------
def status() -> dict:
    """Used by /api/health so you can SEE whether Supabase is really connected."""
    if not supabase_enabled():
        return {"backend": "local", "supabase": "disabled (STORAGE_BACKEND=local or keys missing)"}
    try:
        with _client() as c:
            r = c.get(f"{_url()}/rest/v1/{TABLE}", params={"select": "key", "limit": "1"})
            r.raise_for_status()
        return {"backend": "supabase", "supabase": "connected"}
    except Exception as e:
        return {"backend": "supabase", "supabase": f"ERROR: {str(e)[:120]}"}


def push_all_local() -> int:
    """Re-uploads every local JSON in data/store/ to Supabase. Run after setup, and after any offline work."""
    n = 0
    for kind_dir in sorted(p for p in ROOT.iterdir() if p.is_dir() and p.name != "files"):
        for f in sorted(kind_dir.glob("*.json")):
            save(kind_dir.name, f.stem, json.loads(f.read_text(encoding="utf-8")))
            n += 1
    return n
