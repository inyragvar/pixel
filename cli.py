from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agent.artifacts import ArtifactStore
from agent.config import Settings
from agent.core.executor import Executor
from agent.core.loop import AgentLoop
from agent.core.planner import Planner
from agent.core.reviewer import Reviewer
from agent.providers.factory import build_provider
from agent.run_registry import RunRecord, RunRegistry
from agent.tools.filesystem import FileSystemTool
from agent.tools.git_tools import GitTool
from agent.tools.search import SearchTool
from agent.tools.shell import ShellTool
from agent.tools.validation import ValidationTool
from agent.workspace import WorkspaceManager

app = typer.Typer(add_completion=False)
console = Console()


def _build_runtime(settings: Settings, *, runtime_workspace: Path | None = None, artifacts_workspace: Path | None = None):
    tool_workspace = (runtime_workspace or settings.workspace).resolve()
    artifact_workspace = (artifacts_workspace or settings.workspace).resolve()
    provider_client = build_provider(settings)
    filesystem = FileSystemTool(
        tool_workspace,
        allowlist_patterns=[p.strip() for p in settings.edit_allowlist.split(",") if p.strip()],
        denylist_patterns=[p.strip() for p in settings.edit_denylist.split(",") if p.strip()] or (),
    )
    search = SearchTool(tool_workspace)
    shell = ShellTool(tool_workspace, timeout=settings.command_timeout)
    git = GitTool(tool_workspace)
    validation = ValidationTool(tool_workspace, shell)
    executor = Executor(filesystem, search, shell, git, validation)
    artifact_store = ArtifactStore.create(artifact_workspace / settings.artifacts_dir_name)
    registry = RunRegistry(artifact_workspace / settings.artifacts_dir_name)
    loop = AgentLoop(
        planner=Planner(provider_client, settings.model),
        executor=executor,
        reviewer=Reviewer(provider_client, settings.model),
        provider=provider_client,
        model=settings.model,
        max_steps=settings.max_steps,
        artifact_store=artifact_store,
    )
    return provider_client, executor, artifact_store, registry, loop


def _record_run(
    registry: RunRegistry,
    *,
    artifact_store: ArtifactStore,
    settings: Settings,
    task: str,
    state,
    summary,
) -> None:
    registry.append(
        RunRecord(
            run_id=artifact_store.run_id,
            created_at=datetime.now(UTC).isoformat(),
            task=task,
            provider=settings.provider,
            model=settings.model,
            workspace=str(settings.workspace),
            artifact_dir=str(artifact_store.root),
            step_count=state.step_count,
            finished=state.finished,
            summary=summary.summary,
            changed_files=summary.changed_files,
            commands_run=summary.commands_run,
            next_steps=summary.next_steps,
        )
    )


def _print_run_output(plan, state, summary, artifact_store: ArtifactStore) -> None:
    console.print(Panel(plan.summary, title="Plan Summary"))
    for step in plan.steps:
        console.print(f"- [{step.id}] {step.title}: {step.description}")

    console.print(Panel(f"Steps used: {state.step_count}\nActions: {', '.join(state.actions_taken) or 'none'}", title="Run Stats"))
    if state.history:
        recent_history = "\n\n".join(state.history[-6:])
        console.print(Panel(recent_history, title="Recent Agent History"))

    console.print(Panel(summary.summary, title="Run Summary"))
    console.print(f"Run ID: {artifact_store.run_id}")
    console.print(f"Artifacts: {artifact_store.root}")
    if summary.changed_files:
        console.print("Changed files:")
        for item in summary.changed_files:
            console.print(f"- {item}")

    if summary.commands_run:
        console.print("Commands run:")
        for item in summary.commands_run:
            console.print(f"- {item}")

    if summary.next_steps:
        console.print("Next steps:")
        for item in summary.next_steps:
            console.print(f"- {item}")


def _list_runs(registry: RunRegistry, limit: int) -> None:
    runs = registry.list_runs(limit=limit)
    if not runs:
        console.print("No recorded runs found.")
        return
    table = Table(title="Recorded Runs")
    table.add_column("Run ID")
    table.add_column("Provider")
    table.add_column("Model")
    table.add_column("Steps", justify="right")
    table.add_column("Task")
    table.add_column("Summary")
    for run in runs:
        table.add_row(
            run.run_id,
            run.provider,
            run.model,
            str(run.step_count),
            run.task[:60],
            run.summary[:80],
        )
    console.print(table)


def _replay_run(registry: RunRegistry, run_id: str) -> None:
    payload = registry.load_run_outputs(run_id)
    record = payload["record"]
    console.print(Panel(record["summary"], title=f"Replay: {record['run_id']}"))
    console.print(f"Task: {record['task']}")
    console.print(f"Provider: {record['provider']} | Model: {record['model']}")
    console.print(f"Workspace: {record['workspace']}")
    console.print(f"Artifacts: {record['artifact_dir']}")
    console.print(f"Steps: {record['step_count']} | Finished: {record['finished']}")

    final_summary = payload.get("final_summary")
    if final_summary:
        console.print(Panel(final_summary.get("summary", ""), title="Final Summary"))
        changed_files = final_summary.get("changed_files") or []
        if changed_files:
            console.print("Changed files:")
            for item in changed_files:
                console.print(f"- {item}")

    plan = payload.get("plan")
    if plan:
        console.print(Panel(plan.get("summary", ""), title="Stored Plan"))

    events = payload.get("events") or []
    if events:
        preview = "\n".join(
            f"{event['type']}: {json.dumps(event['payload'], ensure_ascii=False)[:200]}" for event in events[-8:]
        )
        console.print(Panel(preview, title="Recent Events"))


@app.command()
def run(
    task: Optional[str] = typer.Option(None, help="Development task to execute"),
    provider: str = typer.Option("lmstudio", help="Provider name"),
    model: str = typer.Option("qwen/qwen3-coder-30b", help="Model identifier"),
    workspace: Path = typer.Option(Path("."), help="Workspace path"),
    isolated_workspace: bool = typer.Option(False, "--isolated-workspace", help="Run tools against a temporary copy instead of the live workspace"),
    keep_isolated: bool = typer.Option(False, "--keep-isolated", help="Keep the temporary isolated workspace after the run"),
    isolated_base_dir: Optional[Path] = typer.Option(None, "--isolated-base-dir", help="Parent directory for isolated workspace copies"),
    list_runs: bool = typer.Option(False, "--list-runs", help="List past recorded runs and exit"),
    replay_run: Optional[str] = typer.Option(None, "--replay-run", help="Replay a past run by run ID and exit"),
    runs_limit: int = typer.Option(20, "--runs-limit", help="Maximum number of past runs to show"),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON instead of Rich-formatted output for task runs"),
) -> None:
    settings = Settings(provider=provider, model=model, workspace=workspace.resolve())
    registry = RunRegistry(settings.workspace / settings.artifacts_dir_name)

    if list_runs:
        _list_runs(registry, runs_limit)
        return

    if replay_run is not None:
        _replay_run(registry, replay_run)
        return

    if not task:
        raise typer.BadParameter("--task is required unless --list-runs or --replay-run is used")

    workspace_handle = WorkspaceManager(
        settings.workspace,
        enabled=isolated_workspace,
        keep_isolated=keep_isolated,
        base_dir=isolated_base_dir,
    ).prepare()
    try:
        _, _, artifact_store, registry, loop = _build_runtime(
            settings,
            runtime_workspace=workspace_handle.root_path,
            artifacts_workspace=settings.workspace,
        )
        plan, state, summary = loop.run(task)
        if isolated_workspace:
            state.notes.append(f"Workspace mode: {workspace_handle.mode}; root={workspace_handle.root_path}")
            if keep_isolated:
                summary.next_steps = [
                    f"Review isolated workspace: {workspace_handle.root_path}",
                    *summary.next_steps,
                ]
            else:
                summary.next_steps = [
                    "Run again with --keep-isolated if you want to inspect the temporary workspace after completion.",
                    *summary.next_steps,
                ]
        _record_run(
            registry,
            artifact_store=artifact_store,
            settings=settings,
            task=task,
            state=state,
            summary=summary,
        )
        if json_output:
            payload = {
                "run_id": artifact_store.run_id,
                "artifact_dir": str(artifact_store.root),
                "plan": plan.model_dump() if hasattr(plan, "model_dump") else plan,
                "summary": summary.model_dump() if hasattr(summary, "model_dump") else summary,
                "state": {
                    "step_count": state.step_count,
                    "finished": state.finished,
                    "actions_taken": state.actions_taken,
                    "changed_files": sorted(set(state.changed_files)),
                    "commands_run": state.commands_run,
                },
                "workspace": {
                    "mode": workspace_handle.mode,
                    "root": str(workspace_handle.root_path),
                    "kept": bool(isolated_workspace and keep_isolated),
                },
            }
            console.print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            _print_run_output(plan, state, summary, artifact_store)
            if isolated_workspace:
                console.print(f"Workspace mode: isolated copy at {workspace_handle.root_path}")
                if not keep_isolated:
                    console.print("Isolated workspace will be removed after this run. Use --keep-isolated to inspect it.")
    finally:
        workspace_handle.cleanup()


if __name__ == "__main__":
    app()
