from pathlib import Path

from agent.workspace import WorkspaceManager


def test_workspace_manager_creates_isolated_copy(tmp_path: Path) -> None:
    source = tmp_path / "repo"
    source.mkdir()
    (source / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (source / ".git").mkdir()
    (source / ".venv").mkdir()
    (source / ".venv" / "ignore.txt").write_text("no\n", encoding="utf-8")

    manager = WorkspaceManager(source, enabled=True, keep_isolated=False)
    workspace = manager.prepare()

    assert workspace.mode == "copy"
    assert workspace.root_path != source
    assert (workspace.root_path / "main.py").read_text(encoding="utf-8") == "print('hi')\n"
    assert not (workspace.root_path / ".venv").exists()
    assert (source / "main.py").exists()

    manager_path = workspace.root_path
    workspace.cleanup()
    assert not manager_path.exists()


def test_workspace_manager_can_run_live_when_disabled(tmp_path: Path) -> None:
    source = tmp_path / "repo"
    source.mkdir()
    manager = WorkspaceManager(source, enabled=False)
    workspace = manager.prepare()
    assert workspace.mode == "live"
    assert workspace.root_path == source
