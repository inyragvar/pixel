from __future__ import annotations

from agent.config import Settings
from agent.providers.config import ProviderConfig, default_capabilities_for_provider
from agent.providers.openai_compatible import OpenAICompatibleProvider


def build_provider(settings: Settings):
    provider_name = settings.provider.strip().lower()
    if provider_name in {"lmstudio", "ollama", "openai-compatible", "openai"}:
        cfg = ProviderConfig(
            name=provider_name,
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            capabilities=default_capabilities_for_provider(provider_name),
        )
        return OpenAICompatibleProvider(
            base_url=cfg.base_url,
            api_key=cfg.api_key,
            provider_name=cfg.name,
            capabilities=cfg.capabilities,
        )
    raise ValueError(f"Unsupported provider: {settings.provider}")
