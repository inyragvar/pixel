from pathlib import Path

from agent.memory.repo_map import RepoMap


def test_repo_map_lists_files(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    outline = RepoMap(tmp_path).build_outline()
    assert "a.txt" in outline
