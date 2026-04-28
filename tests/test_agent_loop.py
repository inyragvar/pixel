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
from agent.tools.validation import ValidationTool


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
                        tool="replace_in_file",
                        args={"path": "main.py", "old": "hello", "new": "hello world"},
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


def test_agent_loop_executes_tool_steps(tmp_path: Path) -> None:
    workspace = tmp_path
    (workspace / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (workspace / ".git").mkdir()

    provider = FakeProvider()
    executor = Executor(
        filesystem=FileSystemTool(workspace),
        search=SearchTool(workspace),
        shell=ShellTool(workspace),
        git=GitTool(workspace),
        validation=ValidationTool(workspace, ShellTool(workspace)),
    )
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
    assert "replace_in_file" in state.actions_taken
    assert summary.changed_files == ["main.py"]
    assert "hello world" in (workspace / "main.py").read_text(encoding="utf-8")


def test_executor_rejects_missing_required_args(tmp_path: Path) -> None:
    executor = Executor(
        filesystem=FileSystemTool(tmp_path),
        search=SearchTool(tmp_path),
        shell=ShellTool(tmp_path),
        git=GitTool(tmp_path),
        validation=ValidationTool(tmp_path, ShellTool(tmp_path)),
    )

    try:
        executor.run_tool("read_file", {})
    except ValueError as exc:
        assert "Missing required argument" in str(exc)
    else:
        raise AssertionError("Expected missing argument validation to fail")


def test_executor_exposes_apply_patch(tmp_path: Path) -> None:
    executor = Executor(
        filesystem=FileSystemTool(tmp_path),
        search=SearchTool(tmp_path),
        shell=ShellTool(tmp_path),
        git=GitTool(tmp_path),
        validation=ValidationTool(tmp_path, ShellTool(tmp_path)),
    )

    assert "apply_patch" in executor.available_tools()


def test_agent_loop_writes_final_git_artifacts(tmp_path: Path) -> None:
    from agent.artifacts import ArtifactStore

    workspace = tmp_path / "repo"
    workspace.mkdir()
    (workspace / "main.py").write_text("print('hello')\n", encoding="utf-8")

    import subprocess

    subprocess.run(["git", "init"], cwd=workspace, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=workspace, check=True)
    subprocess.run(["git", "add", "main.py"], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=workspace, check=True, capture_output=True, text=True)

    provider = FakeProvider()
    artifact_store = ArtifactStore.create(tmp_path / "runs")
    executor = Executor(
        filesystem=FileSystemTool(workspace),
        search=SearchTool(workspace),
        shell=ShellTool(workspace),
        git=GitTool(workspace),
        validation=ValidationTool(workspace, ShellTool(workspace)),
    )
    loop = AgentLoop(
        planner=Planner(provider, "fake-model"),
        executor=executor,
        reviewer=Reviewer(provider, "fake-model"),
        provider=provider,
        model="fake-model",
        max_steps=5,
        artifact_store=artifact_store,
    )

    loop.run("Update greeting")

    assert (artifact_store.root / "outputs" / "final_git_status.txt").exists()
    diff = (artifact_store.root / "outputs" / "final_git_diff.patch").read_text(encoding="utf-8")
    assert "hello world" in diff
