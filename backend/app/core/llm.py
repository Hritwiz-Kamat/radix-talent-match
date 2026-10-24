"""The ONLY place that talks to an LLM. OpenRouter only, with automatic model fallback.

Free models on OpenRouter get rate-limited or disappear. So we keep an ORDERED LIST of models in .env
(OPENROUTER_MODELS=a,b,c). If model `a` fails (429, 404, timeout, empty reply) we try `b`, then `c`.
Find current free models at https://openrouter.ai/models?max_price=0 and paste their ids into .env.
"""
import os
import time

DEFAULT_MODELS = [  # [Guessing] these ids may be stale. Replace via .env.
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-chat-v3-0324:free",
    "qwen/qwen-2.5-72b-instruct:free",
]


def models() -> list[str]:
    raw = os.getenv("OPENROUTER_MODELS", "")
    return [m.strip() for m in raw.split(",") if m.strip()] or DEFAULT_MODELS


def _client(model: str):
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=model, temperature=0, timeout=60, max_retries=0,
                      base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))


def ask(messages: list[tuple[str, str]], retries_per_model: int = 1) -> str:
    """messages = [("system", "..."), ("human", "...")]. Returns the reply text.
    Tries every configured model in order. Raises RuntimeError only if ALL fail."""
    errors = []
    for model in models():
        for attempt in range(retries_per_model + 1):
            try:
                text = _client(model).invoke(messages).content
                if isinstance(text, list):          # some providers return content blocks
                    text = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in text)
                if text and text.strip():
                    return text
                errors.append(f"{model}: empty reply")
            except Exception as e:
                errors.append(f"{model}: {type(e).__name__}: {str(e)[:120]}")
                if "429" in str(e):
                    time.sleep(3)
    raise RuntimeError("All OpenRouter models failed:\n" + "\n".join(errors))
