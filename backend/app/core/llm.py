from __future__ import annotations

import logging
import os
from enum import Enum
from functools import lru_cache
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    GEMINI = "gemini"


def _build_ollama() -> BaseChatModel:
    from langchain_ollama import ChatOllama

    model = os.getenv("OLLAMA_MODEL", "qwen3.5:cloud")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    logger.info("LLM initialized", extra={"provider": "ollama", "model": model, "base_url": base_url})
    return ChatOllama(model=model, base_url=base_url, temperature=0.2)


def _build_gemini() -> BaseChatModel:
    from langchain_google_genai import ChatGoogleGenerativeAI

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
    model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    logger.info("LLM initialized", extra={"provider": "gemini", "model": model})
    return ChatGoogleGenerativeAI(model=model, api_key=api_key, temperature=0.2)


_BUILDERS = {
    LLMProvider.OLLAMA: _build_ollama,
    LLMProvider.GEMINI: _build_gemini,
}


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    raw = os.getenv("LLM_PROVIDER", LLMProvider.OLLAMA.value).lower().strip()
    try:
        provider = LLMProvider(raw)
    except ValueError:
        valid = ", ".join(p.value for p in LLMProvider)
        raise EnvironmentError(f"Invalid LLM_PROVIDER={raw!r}. Valid options: {valid}")
    return _BUILDERS[provider]()


def normalize_llm_output(content: Any) -> str:
    """Always returns a plain string, even if the model outputs a list of parts."""
    if isinstance(content, str):
        return content
    if not content:
        return ""
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
            else:
                parts.append(str(part))
        return "".join(parts)
    return str(content)
