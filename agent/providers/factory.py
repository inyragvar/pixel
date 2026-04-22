from __future__ import annotations

from agent.config import Settings
from agent.providers.openai_compatible import OpenAICompatibleProvider



def build_provider(settings: Settings):
    if settings.provider in {"lmstudio", "ollama", "openai-compatible", "openai"}:
        return OpenAICompatibleProvider(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
        )
    raise ValueError(f"Unsupported provider: {settings.provider}")
