from __future__ import annotations

from dataclasses import dataclass

from agent.providers.capabilities import ProviderCapabilities


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key: str
    capabilities: ProviderCapabilities


def default_capabilities_for_provider(name: str) -> ProviderCapabilities:
    normalized = name.strip().lower()
    if normalized == "openai":
        return ProviderCapabilities(
            supports_native_tools=True,
            supports_json_schema=True,
            supports_beta_parse=True,
            supports_streaming=True,
        )
    if normalized == "ollama":
        return ProviderCapabilities(
            supports_native_tools=True,
            supports_json_schema=True,
            supports_beta_parse=False,
            supports_streaming=True,
        )
    if normalized in {"lmstudio", "openai-compatible"}:
        return ProviderCapabilities(
            supports_native_tools=True,
            supports_json_schema=True,
            supports_beta_parse=False,
            supports_streaming=True,
        )
    return ProviderCapabilities()
