"""
Shared LLM skill extractor used by Role 1 (JD) and Role 2 (Resume).

  Level-4 pattern : prompt + provider + parser + sink
  Level-5 idea    : validate the output; retry only if it fails the gate (with a limit)
  Extra           : disk cache, so the demo works even when the free API is slow/dead

We do NOT use tool-calling / structured-output APIs: many free OpenRouter models don't support them.
Instead: ask for JSON in plain text -> parse -> validate with Pydantic. Works on any model.
"""
import hashlib
import json
import re
from pathlib import Path

from pydantic import BaseModel, ValidationError

from ..schemas import CATEGORY_HELP, ExtractedSkillList, Skill
from . import llm

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache"
MAX_CHARS = 15000

SYSTEM = (
    "You extract skills from documents and map each to exactly one category code.\n"
    "Category codes:\n" + "\n".join(f"- {k}: {v}" for k, v in CATEGORY_HELP.items()) + "\n\n"
    "Rules:\n"
    "- One entry per distinct skill. No duplicates.\n"
    "- 'evidence' = a short quote or reason from the document.\n"
    "- 'confidence' = high | medium | low (how strongly the document supports the skill).\n"
    "- Infer skills from prose, not just keywords (e.g. 'sketch a URL shortener at scale' -> System Design).\n"
    "- Use OTHER only when no category fits.\n\n"
    'Reply with ONLY a JSON object, no markdown, no commentary, exactly this shape:\n'
    '{"skills":[{"skill_name":"...","category_code":"DSA","evidence":"...","confidence":"high","importance":null}]}\n'
    '"importance" is "required" | "preferred" | null (null for resumes).\n'
)


class _LLMOut(BaseModel):
    skills: list[Skill]


def parse_json_reply(text: str) -> dict:
    """Pull the first JSON object out of a reply (handles ```json fences and chatter)."""
    text = re.sub(r"```(?:json)?", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in reply")
    return json.loads(text[start:end + 1])


def _dedupe(skills: list[Skill]) -> list[Skill]:
    seen, out = set(), []
    for s in skills:
        k = s.skill_name.strip().lower()
        if k not in seen:
            seen.add(k)
            out.append(s)
    return out


def _gate(skills: list[Skill]) -> list[str]:
    """Cheap quality gate. Returns a list of problems ([] = pass)."""
    problems = []
    if len(skills) < 3:
        problems.append("fewer than 3 skills extracted; read the whole document again")
    if skills and all(s.category_code == "OTHER" for s in skills):
        problems.append("every skill is OTHER; map them onto the 12 categories")
    return problems


def extract_skills(text: str, *, source_type: str, source_file: str, task_instructions: str,
                   company: str | None = None, role: str | None = None,
                   extras: dict | None = None, max_retries: int = 2,
                   use_cache: bool = True) -> ExtractedSkillList:
    text = text[:MAX_CHARS]
    key = hashlib.sha256(f"{source_type}|{task_instructions}|{text}".encode()).hexdigest()[:24]
    cache_file = CACHE_DIR / f"{source_type}_{key}.json"
    if use_cache and cache_file.exists():
        return ExtractedSkillList(**json.loads(cache_file.read_text(encoding="utf-8")))

    messages = [("system", SYSTEM + task_instructions), ("human", f"DOCUMENT:\n{text}")]
    skills, last_error = [], "no attempt"
    for _ in range(max_retries + 1):
        try:
            reply = llm.ask(messages)
            skills = _dedupe(_LLMOut(**parse_json_reply(reply)).skills)
            problems = _gate(skills)
            if not problems:
                last_error = None
                break
            last_error = "; ".join(problems)
        except (ValueError, ValidationError) as e:       # bad JSON / bad category / missing field
            last_error = str(e)[:300]
        # surgical retry: feed the exact error back, ask for a corrected full answer
        messages = messages[:2] + [("human", f"Your previous answer was rejected: {last_error}. "
                                             "Return the complete corrected JSON object only.")]
    if last_error:
        raise RuntimeError(f"Extraction failed after retries: {last_error}")

    result = ExtractedSkillList(source_type=source_type, source_file=source_file, company=company,
                                role=role, skills=skills, extras=extras or {})
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result
