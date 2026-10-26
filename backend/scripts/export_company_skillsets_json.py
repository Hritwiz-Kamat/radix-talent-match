"""
scripts/export_company_skillsets_json.py
========================================
Export the company-level data from the local CSV snapshot to
  backend/data/talent_check_company_skillsets.json

This JSON file is then picked up by stage-2 of load_company_levels()
(before the CSV fallback), so the demo works fully offline — no CSV
parsing at startup, no Supabase needed.

Usage (run from backend/ directory):
    python scripts/export_company_skillsets_json.py

Output:
    backend/data/talent_check_company_skillsets.json

The output format is the same as the legacy JSON shape so that the
loader requires no changes:
    {
      "roles": [
        {
          "company": "Google LLC",
          "role": "Software Engineer",
          "levels": {"DSA": 9, "COD": 8, ...},
          "aggregate": {"DSA": 9, ...},
          "weights_used": {"DSA": 1.0, ...}
        },
        ...
      ]
    }
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running from backend/ without installing the package
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.talent_check.scoring import load_company_levels_from_csv  # noqa: E402

OUT_FILE = BACKEND_DIR / "data" / "talent_check_company_skillsets.json"


def main() -> None:
    no_supabase = "--no-supabase" in sys.argv

    print("Loading company levels from CSV …", flush=True)
    try:
        roles = load_company_levels_from_csv()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate: every entry must carry aggregate + weights_used so JSON-path works
    for entry in roles:
        if "aggregate" not in entry or "weights_used" not in entry:
            raise ValueError(
                f"CSV loader returned incomplete entry for {entry.get('company')!r} / "
                f"{entry.get('role')!r}: aggregate and weights_used are required"
            )

    payload = {"roles": roles}
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Exported {len(roles)} entries to: {OUT_FILE}")

    # Summary
    from collections import Counter
    by_company = Counter(r["company"] for r in roles)
    in_scope = ["Google LLC", "Microsoft Corporation", "Oracle Financial Services Software"]
    print()
    print("In-scope companies:")
    for co in in_scope:
        print(f"  {co}: {by_company[co]} role(s)")
    others = sum(v for k, v in by_company.items() if k not in in_scope)
    print(f"Other companies (1 role each): {others}")
    print("  (note: ZS Associates, Inc. row 33 kept; row 102 duplicate skipped)")

    # Re-seed Supabase so stage-1 stays in sync with the JSON
    if no_supabase:
        print()
        print("Skipping Supabase reseed (--no-supabase).")
    else:
        print()
        print("Re-seeding Supabase (stage-1) …", flush=True)
        try:
            from dotenv import load_dotenv
            load_dotenv(BACKEND_DIR / ".env")
            from app.core import storage
            storage.save("company_skillsets", "all", payload)
            print("Supabase reseeded — stage-1 is now in sync.")
        except Exception as e:
            print(f"WARNING: Supabase reseed failed (offline?): {e}", file=sys.stderr)
            print("  JSON file is still valid for offline operation (stage-2 fallback).")

    print()
    print("Done.")
    print("  Stage-2 (JSON file): up to date.")
    if not no_supabase:
        print("  Stage-1 (Supabase):  up to date.")
    print("  To force CSV loading, delete the JSON file and set STORAGE_BACKEND=local.")


if __name__ == "__main__":
    main()
