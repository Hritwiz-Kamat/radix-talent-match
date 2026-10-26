"""
Create and populate staging_company_skill_levels in Supabase using the
Management API's SQL endpoint — no browser login needed.

Run from backend/:  python scripts/create_staging_table.py
"""
from __future__ import annotations
import csv, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import httpx

SUPABASE_URL = os.environ["SUPABASE_URL"]                # https://xxx.supabase.co
SERVICE_KEY  = os.environ["SUPABASE_SERVICE_KEY"]
PROJECT_REF  = SUPABASE_URL.replace("https://", "").split(".")[0]   # ezeqfpatojapdpabpymh

CSV_FILE = Path(__file__).resolve().parents[1] / "app" / "talent_check" / "staging_company_skill_levels_rows.csv"

HEADERS = {
    "apikey":        SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type":  "application/json",
}

# ── helpers ──────────────────────────────────────────────────────────────────
def run_sql(sql: str, label: str = "") -> dict:
    """Execute SQL via the Supabase Management API query endpoint."""
    url = f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query"
    # Management API uses a personal access token — not the service role key.
    # Fallback: use PostgREST rpc or the pg connection via the REST API.
    # Since we don't have a PAT, we use the postgres REST endpoint instead.
    raise NotImplementedError("Management API requires a PAT — using PostgREST direct insert instead")


def escape_sql(val: str | None) -> str:
    if not val or val.strip() == "":
        return "NULL"
    return "'" + val.replace("'", "''") + "'"


# ── Step 1: Create the table via PostgREST RPC if available, else via REST ──
print(f"Supabase project: {PROJECT_REF}")
print(f"URL: {SUPABASE_URL}")

# Try: does the table already exist?
check = httpx.get(
    f"{SUPABASE_URL}/rest/v1/staging_company_skill_levels",
    params={"limit": "1"},
    headers=HEADERS,
    timeout=10,
)
print(f"\nTable existence check: HTTP {check.status_code}")

if check.status_code == 200:
    print("Table already exists. Checking row count …")
    count_r = httpx.get(
        f"{SUPABASE_URL}/rest/v1/staging_company_skill_levels",
        params={"select": "id"},
        headers={**HEADERS, "Prefer": "count=exact", "Range": "0-0"},
        timeout=10,
    )
    cr = count_r.headers.get("content-range", "?")
    print(f"  Existing rows: {cr}")
    recreate = input("Drop and recreate? (y/N): ").strip().lower() == "y"
    if not recreate:
        print("Keeping existing table. Exiting.")
        sys.exit(0)

# ── Step 2: Read CSV ──────────────────────────────────────────────────────────
with open(CSV_FILE, newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))
print(f"\nCSV rows to insert: {len(rows)}")

# ── Step 3: Build list of row dicts for bulk insert via PostgREST ────────────
def parse_ts(val: str) -> str | None:
    v = val.strip()
    return v if v else None

records = []
for r in rows:
    records.append({
        "id":                                     int(r["id"]),
        "companies":                              r["companies"].strip() or None,
        "coding":                                 r["coding"].strip() or None,
        "data_structures_and_algorithms":         r["data_structures_and_algorithms"].strip() or None,
        "object_oriented_programming_and_design": r["object_oriented_programming_and_design"].strip() or None,
        "aptitude_and_problem_solving":           r["aptitude_and_problem_solving"].strip() or None,
        "communication_skills":                   r["communication_skills"].strip() or None,
        "ai_native_engineering":                  r["ai_native_engineering"].strip() or None,
        "devops_and_cloud":                       r["devops_and_cloud"].strip() or None,
        "sql_and_design":                         r["sql_and_design"].strip() or None,
        "software_engineering":                   r["software_engineering"].strip() or None,
        "system_design_and_architecture":         r["system_design_and_architecture"].strip() or None,
        "computer_networking":                    r["computer_networking"].strip() or None,
        "operating_system":                       r["operating_system"].strip() or None,
        "processed":                              r["processed"].strip() or None,
        "processed_at":                           parse_ts(r["processed_at"]),
        "error_message":                          r["error_message"].strip() or None,
        "created_at":                             parse_ts(r["created_at"]),
    })

# ── Step 4: If table exists, delete all rows first (truncate via DELETE) ──────
if check.status_code == 200:
    print("Deleting existing rows …")
    del_r = httpx.delete(
        f"{SUPABASE_URL}/rest/v1/staging_company_skill_levels",
        params={"id": "gte.0"},
        headers={**HEADERS, "Prefer": "return=minimal"},
        timeout=30,
    )
    print(f"  DELETE: HTTP {del_r.status_code}")

# ── Step 5: If table doesn't exist, we need to create it.
#    PostgREST can't CREATE TABLE — we'll try the pg-meta endpoint. ───────────
if check.status_code != 200:
    print("\nTable does not exist. Attempting creation via pg-meta API …")
    # The pg-meta API is available at /pg/  on the service role
    columns_payload = {
        "name": "staging_company_skill_levels",
        "schema": "public",
        "columns": [
            {"name": "id",                                      "type": "int4",        "isPrimaryKey": True},
            {"name": "companies",                               "type": "text"},
            {"name": "coding",                                  "type": "text"},
            {"name": "data_structures_and_algorithms",          "type": "text"},
            {"name": "object_oriented_programming_and_design",  "type": "text"},
            {"name": "aptitude_and_problem_solving",            "type": "text"},
            {"name": "communication_skills",                    "type": "text"},
            {"name": "ai_native_engineering",                   "type": "text"},
            {"name": "devops_and_cloud",                        "type": "text"},
            {"name": "sql_and_design",                          "type": "text"},
            {"name": "software_engineering",                    "type": "text"},
            {"name": "system_design_and_architecture",          "type": "text"},
            {"name": "computer_networking",                     "type": "text"},
            {"name": "operating_system",                        "type": "text"},
            {"name": "processed",                               "type": "text"},
            {"name": "processed_at",                            "type": "timestamptz"},
            {"name": "error_message",                           "type": "text"},
            {"name": "created_at",                              "type": "timestamptz"},
        ],
    }
    create_r = httpx.post(
        f"{SUPABASE_URL}/pg/tables",
        json=columns_payload,
        headers=HEADERS,
        timeout=30,
    )
    print(f"  pg-meta CREATE TABLE: HTTP {create_r.status_code}")
    print(f"  Response: {create_r.text[:400]}")
    if create_r.status_code not in (200, 201):
        print("\nERROR: Could not create table via pg-meta.")
        print("Please run the SQL file manually in the Supabase dashboard SQL editor:")
        print(f"  {Path('data/create_staging_company_skill_levels.sql').resolve()}")
        sys.exit(1)

# ── Step 6: Bulk-insert via PostgREST ────────────────────────────────────────
print(f"\nInserting {len(records)} rows via PostgREST …")
insert_r = httpx.post(
    f"{SUPABASE_URL}/rest/v1/staging_company_skill_levels",
    json=records,
    headers={**HEADERS, "Prefer": "return=minimal"},
    timeout=60,
)
print(f"  INSERT: HTTP {insert_r.status_code}")
if insert_r.status_code in (200, 201):
    print("  ✅ Insert successful")
else:
    print(f"  ❌ Error: {insert_r.text[:500]}")
    sys.exit(1)

# ── Step 7: Verify row count ──────────────────────────────────────────────────
verify = httpx.get(
    f"{SUPABASE_URL}/rest/v1/staging_company_skill_levels",
    params={"select": "id"},
    headers={**HEADERS, "Prefer": "count=exact", "Range": "0-0"},
    timeout=10,
)
print(f"\nVerification — content-range: {verify.headers.get('content-range', '?')}")
print("Done.")
