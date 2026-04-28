from __future__ import annotations

import json
from types import SimpleNamespace

from agent.providers.openai_compatible import OpenAICompatibleProvider
from agent.schemas.actions import AgentDecision


class _FakeFunction:
    def __init__(self, name: str, arguments: str) -> None:
        self.name = name
        self.arguments = arguments


class _FakeToolCall:
    def __init__(self, name: str, arguments: str) -> None:
        self.function = _FakeFunction(name, arguments)


class _FakeClient:
    def __init__(self, completion) -> None:
        self._completion = completion
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        self.beta = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(parse=self.parse)))

    def create(self, **kwargs):
        return self._completion

    def parse(self, **kwargs):
        raise RuntimeError("beta parse unsupported")


def _build_provider(completion) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(base_url="http://example.com/v1", api_key="dummy", client=_FakeClient(completion))


def test_decide_action_parses_native_tool_call() -> None:
    message = SimpleNamespace(
        content="Inspect the file first.",
        tool_calls=[_FakeToolCall("read_file", json.dumps({"path": "main.py"}))],
    )
    completion = SimpleNamespace(choices=[SimpleNamespace(message=message)])
    provider = _build_provider(completion)

    decision = provider.decide_action(
        system_prompt="act",
        messages=[{"role": "user", "content": "task"}],
        model="fake-model",
        tools=[],
        decision_schema=AgentDecision,
    )

    assert decision.decision == "tool"
    assert decision.tool is not None
    assert decision.tool.tool == "read_file"
    assert decision.tool.args == {"path": "main.py"}
    assert decision.tool.reasoning == "Inspect the file first."


def test_decide_action_falls_back_to_json_in_text() -> None:
    message = SimpleNamespace(
        content='```json\n{"decision":"final","summary":"done","next_steps":[],"changed_files":[]}\n```',
        tool_calls=[],
    )
    completion = SimpleNamespace(choices=[SimpleNamespace(message=message)])
    provider = _build_provider(completion)

    decision = provider.decide_action(
        system_prompt="act",
        messages=[{"role": "user", "content": "task"}],
        model="fake-model",
        tools=[],
        decision_schema=AgentDecision,
    )

    assert decision.decision == "final"
    assert decision.summary == "done"


def test_provider_honors_disabled_native_tools_and_uses_text_json_fallback() -> None:
    from agent.providers.capabilities import ProviderCapabilities

    message = SimpleNamespace(
        content='{"decision":"final","summary":"done without tools","next_steps":[],"changed_files":[]}',
        tool_calls=[_FakeToolCall("read_file", json.dumps({"path": "ignored.py"}))],
    )
    completion = SimpleNamespace(choices=[SimpleNamespace(message=message)])
    provider = OpenAICompatibleProvider(
        base_url="http://example.com/v1",
        api_key="dummy",
        client=_FakeClient(completion),
        capabilities=ProviderCapabilities(
            supports_native_tools=False,
            supports_json_schema=False,
            supports_beta_parse=False,
        ),
    )

    decision = provider.decide_action(
        system_prompt="act",
        messages=[{"role": "user", "content": "task"}],
        model="fake-model",
        tools=[],
        decision_schema=AgentDecision,
    )

    assert decision.decision == "final"
    assert decision.summary == "done without tools"
    assert provider.last_decision_mode == "text_json_fallback"
