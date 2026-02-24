from __future__ import annotations

import os
from functools import lru_cache

from langchain_ollama import ChatOllama

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemini-3-flash-preview")


@lru_cache(maxsize=1)
def get_llm() -> ChatOllama:
    return ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.2,
    )
