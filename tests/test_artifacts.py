from __future__ import annotations

import json
from pathlib import Path

from agent.artifacts import ArtifactStore
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
                summary="Inspect and validate.",
                steps=[PlanStep(id="1", title="Inspect", description="Read files")],
            )
        if response_schema is AgentDecision:
            if self.calls == 2:
                return AgentDecision(
                    decision="tool",
                    tool=ToolAction(tool="run_command", args={"command": "pwd"}),
                )
            return AgentDecision(
                decision="final",
                summary="Done.",
                changed_files=[],
                next_steps=["Review artifacts"],
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


def test_artifacts_are_written(tmp_path: Path) -> None:
    workspace = tmp_path
    (workspace / ".git").mkdir()

    provider = FakeProvider()
    executor = Executor(
        filesystem=FileSystemTool(workspace),
        search=SearchTool(workspace),
        shell=ShellTool(workspace),
        git=GitTool(workspace),
        validation=ValidationTool(workspace, ShellTool(workspace)),
    )
    artifact_store = ArtifactStore.create(workspace / ".dev-agent" / "runs")
    loop = AgentLoop(
        planner=Planner(provider, "fake-model"),
        executor=executor,
        reviewer=Reviewer(provider, "fake-model"),
        provider=provider,
        model="fake-model",
        max_steps=4,
        artifact_store=artifact_store,
    )

    _, state, summary = loop.run("Inspect repo")

    assert state.artifact_dir == str(artifact_store.root)
    assert summary.summary == "Done."
    assert (artifact_store.root / "task.txt").exists()
    assert (artifact_store.root / "prompts" / "plan_prompt.json").exists()
    assert (artifact_store.root / "prompts" / "step_01_decision_prompt.json").exists()
    assert (artifact_store.root / "outputs" / "plan.json").exists()
    assert (artifact_store.root / "outputs" / "step_01_tool.json").exists()
    assert (artifact_store.root / "outputs" / "step_01_result.txt").exists()
    assert (artifact_store.root / "outputs" / "final_summary.json").exists()
    events = (artifact_store.root / "events.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert any(json.loads(line)["type"] == "run_started" for line in events)
    assert any(json.loads(line)["type"] == "tool_result" for line in events)
