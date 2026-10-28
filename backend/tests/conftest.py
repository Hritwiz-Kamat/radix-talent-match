import os

# During automated test runs, default to offline local storage and empty OpenRouter key
os.environ.setdefault("STORAGE_BACKEND", "local")
os.environ.setdefault("OPENROUTER_API_KEY", "")
