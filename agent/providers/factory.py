from __future__ import annotations

from agent.config import Settings
from agent.providers.config import ProviderConfig, default_capabilities_for_provider
from agent.providers.openai_compatible import OpenAICompatibleProvider


def build_provider(settings: Settings):
    normalized = settings.provider.strip().lower()
    if normalized in {"lmstudio", "ollama", "openai-compatible", "openai"}:
        config = ProviderConfig(
            name=normalized,
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            capabilities=default_capabilities_for_provider(normalized),
        )
        return OpenAICompatibleProvider(config=config)
    raise ValueError(f"Unsupported provider: {settings.provider}")
