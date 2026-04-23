from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from agent.config import Settings
from agent.core.executor import Executor
from agent.core.loop import AgentLoop
from agent.core.planner import Planner
from agent.core.reviewer import Reviewer
from agent.providers.factory import build_provider
from agent.tools.filesystem import FileSystemTool
from agent.tools.git_tools import GitTool
from agent.tools.search import SearchTool
from agent.tools.shell import ShellTool
from agent.workspace import WorkspaceManager

app = typer.Typer(add_completion=False)
console = Console()


@app.command()
def run(
    task: str = typer.Option(..., help="Development task to execute"),
    provider: str = typer.Option("lmstudio", help="Provider name"),
    model: str = typer.Option("qwen/qwen3-coder-30b", help="Model identifier"),
    workspace: Path = typer.Option(Path("."), help="Workspace path"),
    isolate: bool = typer.Option(True, "--isolate/--no-isolate", help="Run in an isolated workspace copy"),
    keep_workspace: bool = typer.Option(False, "--keep-workspace", help="Keep the isolated workspace after the run"),
) -> None:
    settings = Settings(
        provider=provider,
        model=model,
        workspace=workspace.resolve(),
        isolate_workspace=isolate,
        keep_isolated_workspace=keep_workspace,
    )
    provider_client = build_provider(settings)

    workspace_manager = WorkspaceManager(
        settings.workspace,
        enabled=settings.isolate_workspace,
        keep_isolated=settings.keep_isolated_workspace,
    )
    run_workspace = workspace_manager.prepare()

    filesystem = FileSystemTool(
        run_workspace.root_path,
        allowlist_patterns=settings.edit_allowlist or None,
        denylist_patterns=settings.edit_denylist or None,
    )
    search = SearchTool(run_workspace.root_path)
    shell = ShellTool(run_workspace.root_path, timeout=settings.command_timeout)
    git = GitTool(run_workspace.root_path)
    executor = Executor(filesystem, search, shell, git)

    loop = AgentLoop(
        planner=Planner(provider_client, settings.model),
        executor=executor,
        reviewer=Reviewer(provider_client, settings.model),
        provider=provider_client,
        model=settings.model,
        max_steps=settings.max_steps,
    )

    try:
        plan, state, summary = loop.run(task)
    finally:
        if settings.keep_isolated_workspace:
            console.print(f"Workspace kept at: {run_workspace.root_path}")
        elif settings.isolate_workspace:
            console.print(f"Isolated workspace: {run_workspace.root_path}")

    console.print(Panel(f"Mode: {run_workspace.mode}\nSource: {run_workspace.source_path}\nActive: {run_workspace.root_path}", title="Workspace"))
    console.print(Panel(plan.summary, title="Plan Summary"))
    for step in plan.steps:
        console.print(f"- [{step.id}] {step.title}: {step.description}")

    console.print(Panel(f"Steps used: {state.step_count}\nActions: {', '.join(state.actions_taken) or 'none'}", title="Run Stats"))
    if state.history:
        recent_history = "\n\n".join(state.history[-6:])
        console.print(Panel(recent_history, title="Recent Agent History"))

    console.print(Panel(summary.summary, title="Run Summary"))
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

    if settings.isolate_workspace and not settings.keep_isolated_workspace:
        run_workspace.cleanup()


if __name__ == "__main__":
    app()
