from __future__ import annotations

import logging
import os
from functools import lru_cache

from langchain_ollama import ChatOllama

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_llm() -> ChatOllama:
    model = os.getenv("OLLAMA_MODEL", "gemini-3-flash-preview")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    logger.info("LLM initialized for analysis", extra={"model": model, "base_url": base_url})
    return ChatOllama(model=model, base_url=base_url, temperature=0.2)
