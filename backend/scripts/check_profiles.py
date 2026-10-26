"""
Root-cause trace: why does _test_no_name_profile appear in /candidates?
Checks both local mirror and Supabase.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))
from dotenv import load_dotenv; load_dotenv(".env")

from pathlib import Path
import json

print("=== 1. Local mirror (data/store/profiles/) ===")
local_dir = Path("data/store/profiles")
local_keys = sorted(p.stem for p in local_dir.glob("*.json")) if local_dir.exists() else []
print(f"  keys: {local_keys}")

print()
print("=== 2. storage.list_keys('profiles') ===")
from app.core import storage
keys = storage.list_keys("profiles")
print(f"  keys: {keys}")
print(f"  type: {type(keys)}")

print()
print("=== 3. STORAGE_BACKEND env var ===")
backend_mode = os.environ.get("STORAGE_BACKEND", "(not set)")
supabase_url = os.environ.get("SUPABASE_URL", "(not set)")
print(f"  STORAGE_BACKEND: {backend_mode}")
print(f"  SUPABASE_URL present: {'yes' if supabase_url != '(not set)' else 'no'}")

print()
print("=== 4. Is _test_no_name_profile in local store? ===")
test_local = local_dir / "_test_no_name_profile.json"
print(f"  local file exists: {test_local.exists()}")

print()
print("=== 5. Is _test_no_name_profile in Supabase? ===")
# Try loading it directly via storage.load
raw = storage.load("profiles", "_test_no_name_profile")
print(f"  storage.load result: {raw}")
if raw:
    print("  -> Profile IS in Supabase (or was cached). This is the root cause.")
else:
    print("  -> Profile not found in storage.")

print()
print("=== 6. Inspect storage.py to understand list_keys source ===")
import inspect
storage_src = inspect.getsourcefile(storage)
print(f"  storage module: {storage_src}")
# Read relevant section
src = Path(storage_src).read_text(encoding="utf-8")
# Find list_keys function
start = src.find("def list_keys")
end = src.find("\ndef ", start + 1)
print(f"\n  list_keys source:\n")
for line in src[start:end].splitlines():
    print(f"    {line}")
