"""Pushes all local JSON (4 candidate profiles, extraction results, company levels) into Supabase.
Run from backend/:   python scripts/seed_supabase.py
Safe to run repeatedly (upsert)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
import os
os.environ["STORAGE_STRICT"] = "1"          # fail loudly here: a silent failure would defeat the point
from app.core import storage

print("Before:", storage.status())
if not storage.supabase_enabled():
    sys.exit("Supabase not configured: set SUPABASE_URL and SUPABASE_SERVICE_KEY in backend/.env")

# company levels: use the real file if present, otherwise the placeholder
data_dir = Path(__file__).resolve().parents[1] / "data"
real = data_dir / "talent_check_company_skillsets.json"
src = real if real.exists() else data_dir / "talent_check_company_skillsets.PLACEHOLDER.json"
storage.save("company_skillsets", "all", json.loads(src.read_text(encoding="utf-8")))
print("company levels from:", src.name)

print("Pushed", storage.push_all_local(), "documents")
print("After:", storage.status())
