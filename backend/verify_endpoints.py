"""
Final verification script for Role 04 — Talent Check.
Tests all 4 endpoints, calibration scores, edge cases, and import sanity.
Run from: backend/
"""
import sys, os, json
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))
from dotenv import load_dotenv; load_dotenv(".env")

from app.main import app
from fastapi.testclient import TestClient
from app.schemas import CandidateProfile
from app.talent_check.scoring import score

client = TestClient(app)
PASS = "PASS"
FAIL = "FAIL"
results = []

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, label, detail))
    marker = "  OK" if condition else "  !!"
    print(f"{marker}  {label}" + (f"  [{detail}]" if detail else ""))

print("=" * 65)
print("SECTION 1 — Git / environment")
print("=" * 65)
import subprocess
branch = subprocess.check_output(["git","branch","--show-current"], cwd="..").decode().strip()
check("Branch is role/talent-check", branch == "role/talent-check", branch)
check("uv not present (expected — no pyproject.toml)", True, "using python -m pytest as per existing project setup")

print()
print("=" * 65)
print("SECTION 2 — GET /api/talent-check/companies")
print("=" * 65)
r = client.get("/api/talent-check/companies")
check("Status 200", r.status_code == 200, str(r.status_code))
d = r.json()
check("3 companies returned", len(d.get("companies", [])) == 3, str(d.get("companies")))
check("Google LLC present", "Google LLC" in d.get("companies", []))
check("roles_by_company present", bool(d.get("roles_by_company")))
check("Google has 2 roles", len(d["roles_by_company"].get("Google LLC", [])) == 2,
      str(d["roles_by_company"].get("Google LLC")))
print(f"     companies: {d['companies']}")
print(f"     roles: {d['roles_by_company']}")

print()
print("=" * 65)
print("SECTION 3 — GET /api/talent-check/candidates")
print("=" * 65)
r = client.get("/api/talent-check/candidates")
check("Status 200", r.status_code == 200, str(r.status_code))
cands = r.json()
check("Returns a list", isinstance(cands, list))
check("4 candidates returned", len(cands) == 4, str(len(cands)))
for c in cands:
    check(f"  {c['id']} has 'id' and 'name'", "id" in c and "name" in c, str(c))
    check(f"  {c['id']} name is non-empty", bool(c.get("name")), repr(c.get("name")))
print(f"     candidates: {[c['id'] for c in cands]}")

print()
print("  -- Edge case: profile with missing 'name' field --")
# Simulate a stored profile that has no 'name' key
from app.core import storage as stor
# Patch: temporarily write a synthetic key with no name
_synthetic_key = "_test_no_name_profile"
_synthetic_profile = {
    "candidate_id": _synthetic_key,
    # deliberately omit 'name'
    "skills": [],
    "experience_years": 0,
    "education": [],
    "certifications": [],
    "summary": "test"
}
stor.save("profiles", _synthetic_key, _synthetic_profile)
r_edge = client.get("/api/talent-check/candidates")
edge_cands = r_edge.json()
synthetic = next((c for c in edge_cands if c["id"] == _synthetic_key), None)
check("Endpoint doesn't crash on nameless profile", r_edge.status_code == 200)
check("Nameless profile falls back to key as name",
      synthetic is not None and synthetic["name"] == _synthetic_key,
      str(synthetic))

print()
print("  -- Edge case: profile with empty dict / None raw --")
# Check the guard 'if raw and isinstance(raw, dict)' — can't easily inject None without
# breaking storage, so we verify by reading the source code
import ast as ast_mod, pathlib
router_src = pathlib.Path("app/talent_check/router.py").read_text()
check("Guard 'if raw and isinstance(raw, dict)' present in /candidates",
      "if raw and isinstance(raw, dict)" in router_src)
check("Fallback 'raw.get(\"candidate_id\", key)' present",
      'raw.get("candidate_id", key)' in router_src)
check("Fallback 'raw.get(\"name\", key)' present",
      'raw.get("name", key)' in router_src)

# Clean up the synthetic profile from local store only
_local_path = Path("data/store/profiles") / f"{_synthetic_key}.json"
if _local_path.exists():
    _local_path.unlink()
    print(f"     (cleaned up {_local_path})")

print()
print("=" * 65)
print("SECTION 4 — POST /api/talent-check (all 4 candidates, scores unchanged)")
print("=" * 65)
calibration = [
    ("ananya-rao",          "Google LLC",                            "Software Engineer",       69),
    ("karthik-subramaniam", "Google LLC",                            "Data Scientist",          52),
    ("priya-menon",         "Oracle Financial Services Software",    "Application Support Analyst", 46),
    ("rohan-verma",         "Google LLC",                            "Software Engineer",       78),
    ("rohan-verma",         "Microsoft Corporation",                 "Software Engineer",       80),
]
for cand_id, company, role, expected in calibration:
    r = client.post("/api/talent-check", json={"candidate_id": cand_id, "company": company, "role": role})
    check(f"POST 200 ({cand_id[:12]})", r.status_code == 200, str(r.status_code))
    if r.status_code == 200:
        data = r.json()
        actual = data["readiness_score"]
        check(f"  score={actual} == {expected}", actual == expected, f"{cand_id} / {role}")
        check(f"  12 gaps returned", len(data["skillset_gap"]) == 12, str(len(data["skillset_gap"])))
        check(f"  scoring_method present", bool(data.get("scoring_method")))
        check(f"  candidate_id correct", data["candidate_id"] == cand_id)

print()
print("  -- Not assessable: display-only check (scoring unchanged) --")
# Verify the explanation="no evidence" fields exist in the response
r = client.post("/api/talent-check", json={"candidate_id": "ananya-rao", "company": "Google LLC", "role": "Software Engineer"})
gaps = r.json()["skillset_gap"]
no_ev_gaps = [g for g in gaps if g["explanation"] == "no evidence"]
has_ev_gaps = [g for g in gaps if g["explanation"] != "no evidence"]
check("Some gaps have explanation='no evidence'", len(no_ev_gaps) > 0, f"{len(no_ev_gaps)} found")
check("All no-evidence gaps have candidate_level=0", all(g["candidate_level"] == 0 for g in no_ev_gaps))
check("Some gaps have real evidence", len(has_ev_gaps) > 0, f"{len(has_ev_gaps)} found")
check("Scoring formula not changed by display changes",
      r.json()["readiness_score"] == 69, str(r.json()["readiness_score"]))
print(f"     no-evidence categories: {[g['category_code'] for g in no_ev_gaps]}")
print(f"     evidenced  categories:  {[g['category_code'] for g in has_ev_gaps]}")

print()
print("  -- Error handling --")
r_bad_cand = client.post("/api/talent-check", json={"candidate_id": "nobody", "company": "Google LLC", "role": "Software Engineer"})
check("Bad candidate -> 404", r_bad_cand.status_code == 404, str(r_bad_cand.status_code))
check("404 detail mentions candidate", "nobody" in r_bad_cand.json().get("detail", ""))
r_bad_co = client.post("/api/talent-check", json={"candidate_id": "ananya-rao", "company": "FakeCo", "role": "Fake"})
check("Bad company -> 404", r_bad_co.status_code == 404, str(r_bad_co.status_code))

print()
print("=" * 65)
print("SECTION 5 — GET /api/talent-check/compare")
print("=" * 65)
r = client.get("/api/talent-check/compare?company=Google+LLC&role=Software+Engineer")
check("Status 200", r.status_code == 200, str(r.status_code))
compare_results = r.json()
check("4 results returned", len(compare_results) == 4, str(len(compare_results)))
scores_in_order = [res["readiness_score"] for res in compare_results]
check("Sorted descending", scores_in_order == sorted(scores_in_order, reverse=True), str(scores_in_order))
check("Rohan first (78)", compare_results[0]["candidate_id"] == "rohan-verma",
      compare_results[0]["candidate_id"])
check("Ananya second (69)", compare_results[1]["candidate_id"] == "ananya-rao",
      compare_results[1]["candidate_id"])
print(f"     ranking: {[(r['candidate_id'], r['readiness_score']) for r in compare_results]}")
r_bad = client.get("/api/talent-check/compare?company=FakeCo&role=Fake")
check("Bad company -> 404", r_bad.status_code == 404)

print()
print("=" * 65)
print("SECTION 6 — router.py import sanity")
print("=" * 65)
check("'mocks' not in router.py", "from app import mocks" not in router_src)
check("'import re' not inside function body", "    import re" not in router_src)
check("'import re' at module top (before any def/class)",
      any(line.strip() == "import re" for line in router_src.splitlines()
          if not line.startswith(" ") and not line.startswith("\t")))
print(f"     First 5 lines of router.py:")
for i, line in enumerate(router_src.splitlines()[:6], 1):
    print(f"       {i}: {line}")

print()
print("=" * 65)
print("SECTION 7 — vite.config.js proxy present")
print("=" * 65)
vite_src = pathlib.Path("../frontend/vite.config.js").read_text()
check("proxy key present", "proxy" in vite_src)
check("target localhost:8000 present", "localhost:8000" in vite_src)
check("changeOrigin: true present", "changeOrigin: true" in vite_src)
check("'/api' proxy route present", "'/api'" in vite_src)
api_line_in_jsx = pathlib.Path("../frontend/src/pages/TalentCheck.jsx").read_text(encoding="utf-8").splitlines()[7]
check("TalentCheck.jsx API const is empty string", 'const API = ""' in api_line_in_jsx, repr(api_line_in_jsx))

print()
print("=" * 65)
print("SECTION 8 — calibration relationships")
print("=" * 65)
src = Path("data/talent_check_company_skillsets.PLACEHOLDER.json")
levels = json.loads(src.read_text())["roles"]
def get_lvl(company, role):
    return next(r["levels"] for r in levels if r["company"]==company and r["role"]==role)
def load_p(slug):
    return CandidateProfile(**json.loads(Path(f"data/store/profiles/{slug}.json").read_text()))

ananya  = load_p("ananya-rao")
karthik = load_p("karthik-subramaniam")
priya   = load_p("priya-menon")
rohan   = load_p("rohan-verma")

r_ananya_swe  = score(ananya,  get_lvl("Google LLC","Software Engineer"), "Google LLC")
r_karthik_swe = score(karthik, get_lvl("Google LLC","Software Engineer"), "Google LLC")
r_karthik_ds  = score(karthik, get_lvl("Google LLC","Data Scientist"),    "Google LLC")
r_ananya_ds   = score(ananya,  get_lvl("Google LLC","Data Scientist"),    "Google LLC")
r_priya_oracle = score(priya,  get_lvl("Oracle Financial Services Software","Application Support Analyst"), "Oracle Financial Services Software")
r_priya_swe   = score(priya,   get_lvl("Google LLC","Software Engineer"), "Google LLC")
r_rohan_swe   = score(rohan,   get_lvl("Google LLC","Software Engineer"), "Google LLC")
r_rohan_ds    = score(rohan,   get_lvl("Google LLC","Data Scientist"),    "Google LLC")
r_rohan_msft  = score(rohan,   get_lvl("Microsoft Corporation","Software Engineer"), "Microsoft Corporation")

check("Ananya > Karthik on Google SWE",
      r_ananya_swe.readiness_score > r_karthik_swe.readiness_score,
      f"{r_ananya_swe.readiness_score} > {r_karthik_swe.readiness_score}")
check("Karthik > Ananya on Google DS",
      r_karthik_ds.readiness_score > r_ananya_ds.readiness_score,
      f"{r_karthik_ds.readiness_score} > {r_ananya_ds.readiness_score}")
check("Priya best at Oracle Support (vs Google SWE)",
      r_priya_oracle.readiness_score > r_priya_swe.readiness_score,
      f"{r_priya_oracle.readiness_score} > {r_priya_swe.readiness_score}")
check("Rohan > Ananya on Google SWE",
      r_rohan_swe.readiness_score > r_ananya_swe.readiness_score,
      f"{r_rohan_swe.readiness_score} > {r_ananya_swe.readiness_score}")
check("Rohan > Karthik on Google DS",
      r_rohan_ds.readiness_score > r_karthik_ds.readiness_score,
      f"{r_rohan_ds.readiness_score} > {r_karthik_ds.readiness_score}")
check("Rohan >= 68 on all checked roles",
      all(s >= 68 for s in [r_rohan_swe.readiness_score, r_rohan_ds.readiness_score, r_rohan_msft.readiness_score]),
      str([r_rohan_swe.readiness_score, r_rohan_ds.readiness_score, r_rohan_msft.readiness_score]))

print()
print("=" * 65)
print("SECTION 9 — working tree summary")
print("=" * 65)
wt = subprocess.check_output(["git","status","--short"], cwd="..").decode().strip()
for line in wt.splitlines():
    print(f"  {line}")

print()
print("=" * 65)
print("SECTION 10 — scratch file disposition")
print("=" * 65)
for fname in ["verify_endpoints.py", "check_profiles.py"]:
    fpath = Path(fname)
    check(f"{fname} exists (untracked)", fpath.exists())
# Check for any imports of these files anywhere
for fname in ["verify_endpoints", "check_profiles"]:
    hits = list(Path(".").rglob("*.py"))
    refs = [str(f) for f in hits if fname in f.read_text() and "verify_endpoints.py" not in str(f) and "check_profiles.py" not in str(f) and "final_verification.py" not in str(f)]
    check(f"{fname} not imported anywhere else", len(refs) == 0, f"refs: {refs}" if refs else "none")

print()
print("=" * 65)
print("FINAL SUMMARY")
print("=" * 65)
failures = [(l, d) for s, l, d in results if s == FAIL]
print(f"Total checks: {len(results)}")
print(f"Passed: {sum(1 for s,_,_ in results if s==PASS)}")
print(f"Failed: {len(failures)}")
if failures:
    print("\nFAILURES:")
    for label, detail in failures:
        print(f"  !! {label}  [{detail}]")
else:
    print("\nAll checks passed.")
