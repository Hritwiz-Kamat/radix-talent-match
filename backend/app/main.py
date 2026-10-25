import importlib
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    from app.talent_check.scoring import load_company_levels_with_source
    levels, source = load_company_levels_with_source()
    log.info("Talent Check company skillsets loaded from %s (%d entries)", source, len(levels))
    yield


app = FastAPI(title="RADIX Talent Match", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])

MODULES = ["jd_analytics", "resume_parsing", "profile_builder", "talent_check", "skill_matching"]
for name in MODULES:
    target = f"app.{name}.router"
    try:
        app.include_router(importlib.import_module(target).router)
    except ModuleNotFoundError as e:
        if e.name != target:      # a real missing dependency -> show it, don't hide it
            raise
        print(f"[main] {name}: no router.py yet (skipping)")


@app.get("/api/health")
def health():
    from app.schemas import CONTRACT_VERSION
    from app.core import storage
    return {"ok": True, "contract": CONTRACT_VERSION, "storage": storage.status()}


@app.get("/api/mock/{kind}")
def mock(kind: str):
    """Fake-but-valid data so frontend work never waits on backend work."""
    from app import mocks
    table = {"jd": mocks.MOCK_JD, "resume": mocks.MOCK_RESUME, "profile": mocks.MOCK_PROFILE,
             "talent-check": mocks.MOCK_TALENT_CHECK, "skill-match": mocks.MOCK_MATCH}
    return table[kind]
