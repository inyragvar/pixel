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

app = typer.Typer(add_completion=False)
console = Console()


@app.command()
def run(
    task: str = typer.Option(..., help="Development task to execute"),
    provider: str = typer.Option("lmstudio", help="Provider name"),
    model: str = typer.Option("qwen/qwen3-coder-30b", help="Model identifier"),
    workspace: Path = typer.Option(Path("."), help="Workspace path"),
) -> None:
    settings = Settings(provider=provider, model=model, workspace=workspace.resolve())
    provider_client = build_provider(settings)

    filesystem = FileSystemTool(
        settings.workspace,
        allowlist_patterns=settings.edit_allowlist or None,
        denylist_patterns=settings.edit_denylist or None,
    )
    search = SearchTool(settings.workspace)
    shell = ShellTool(settings.workspace, timeout=settings.command_timeout)
    git = GitTool(settings.workspace)
    executor = Executor(filesystem, search, shell, git)

    loop = AgentLoop(
        planner=Planner(provider_client, settings.model),
        executor=executor,
        reviewer=Reviewer(provider_client, settings.model),
        provider=provider_client,
        model=settings.model,
        max_steps=settings.max_steps,
    )

    plan, state, summary = loop.run(task)

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


if __name__ == "__main__":
    app()
