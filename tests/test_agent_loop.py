from __future__ import annotations

from pathlib import Path

from agent.core.executor import Executor
from agent.core.loop import AgentLoop
from agent.core.planner import Planner
from agent.core.reviewer import Reviewer
from agent.schemas.actions import AgentDecision, ToolAction
from agent.schemas.outputs import FinalAnswer
from agent.schemas.plan import Plan, PlanStep
from agent.tools.filesystem import FileSystemTool
from agent.tools.git_tools import GitTool
from agent.tools.search import SearchTool
from agent.tools.shell import ShellTool


class FakeProvider:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, *, system_prompt, messages, model, response_schema=None):
        self.calls += 1
        if response_schema is Plan:
            return Plan(
                summary="Inspect, modify, validate.",
                steps=[PlanStep(id="1", title="Inspect", description="Read the file")],
            )
        if response_schema is AgentDecision:
            if self.calls == 2:
                return AgentDecision(
                    decision="tool",
                    tool=ToolAction(tool="read_file", args={"path": "main.py"}),
                )
            if self.calls == 3:
                return AgentDecision(
                    decision="tool",
                    tool=ToolAction(
                        tool="apply_patch",
                        args={
                            "patch": """--- a/main.py
+++ b/main.py
@@ -1 +1 @@
-print('hello')
+print('hello world')
"""
                        },
                    ),
                )
            return AgentDecision(
                decision="final",
                summary="Implemented the requested change.",
                changed_files=["main.py"],
            )
        if response_schema is FinalAnswer:
            return FinalAnswer(summary="Fallback summary")
        raise AssertionError("Unexpected schema")

    def decide_action(self, *, system_prompt, messages, model, tools, decision_schema):
        return self.generate(
            system_prompt=system_prompt,
            messages=messages,
            model=model,
            response_schema=decision_schema,
        )


class FakeRollbackProvider(FakeProvider):
    def generate(self, *, system_prompt, messages, model, response_schema=None):
        self.calls += 1
        if response_schema is Plan:
            return Plan(summary="Try edit then rollback.", steps=[])
        if response_schema is AgentDecision:
            if self.calls == 2:
                return AgentDecision(
                    decision="tool",
                    tool=ToolAction(tool="write_file", args={"path": "temp.txt", "content": "oops\n"}),
                )
            if self.calls == 3:
                return AgentDecision(
                    decision="tool",
                    tool=ToolAction(tool="rollback_all", args={}),
                )
            return AgentDecision(decision="final", summary="Rolled back safely.")
        if response_schema is FinalAnswer:
            return FinalAnswer(summary="Fallback summary")
        raise AssertionError("Unexpected schema")


def _build_executor(workspace: Path) -> Executor:
    return Executor(
        filesystem=FileSystemTool(workspace),
        search=SearchTool(workspace),
        shell=ShellTool(workspace),
        git=GitTool(workspace),
    )


def test_agent_loop_executes_tool_steps(tmp_path: Path) -> None:
    workspace = tmp_path
    (workspace / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (workspace / ".git").mkdir()

    provider = FakeProvider()
    executor = _build_executor(workspace)
    loop = AgentLoop(
        planner=Planner(provider, "fake-model"),
        executor=executor,
        reviewer=Reviewer(provider, "fake-model"),
        provider=provider,
        model="fake-model",
        max_steps=5,
    )

    plan, state, summary = loop.run("Update greeting")

    assert plan.summary == "Inspect, modify, validate."
    assert state.finished is True
    assert "read_file" in state.actions_taken
    assert "apply_patch" in state.actions_taken
    assert summary.changed_files == ["main.py"]
    assert state.tracked_files == ["main.py"]
    assert "hello world" in (workspace / "main.py").read_text(encoding="utf-8")


def test_agent_loop_can_rollback_changes(tmp_path: Path) -> None:
    workspace = tmp_path
    (workspace / ".git").mkdir()

    provider = FakeRollbackProvider()
    executor = _build_executor(workspace)
    loop = AgentLoop(
        planner=Planner(provider, "fake-model"),
        executor=executor,
        reviewer=Reviewer(provider, "fake-model"),
        provider=provider,
        model="fake-model",
        max_steps=5,
    )

    _, state, summary = loop.run("Test rollback")

    assert state.finished is True
    assert "rollback_all" in state.actions_taken
    assert state.tracked_files == []
    assert not (workspace / "temp.txt").exists()
    assert summary.summary == "Rolled back safely."
