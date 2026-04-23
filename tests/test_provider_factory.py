from agent.config import Settings
from agent.providers.factory import build_provider
import agent.providers.openai_compatible as openai_compatible


class _DummyOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def test_factory_builds_provider_with_capabilities(monkeypatch) -> None:
    monkeypatch.setattr(openai_compatible, "OpenAI", _DummyOpenAI)

    settings = Settings(
        provider="ollama",
        model="dummy-model",
        openai_base_url="http://example.com/v1",
        openai_api_key="dummy",
    )
    provider = build_provider(settings)

    assert provider.provider_name == "ollama"
    assert provider.capabilities.supports_native_tools is True
    assert provider.capabilities.supports_json_schema is True
    assert provider.capabilities.supports_beta_parse is False
