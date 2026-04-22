from __future__ import annotations

from pathlib import Path


class RepoMap:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

    def build_outline(self, max_files: int = 200) -> str:
        files = []
        for path in sorted(self.workspace.rglob("*")):
            if path.is_file() and ".git" not in path.parts:
                files.append(str(path.relative_to(self.workspace)))
            if len(files) >= max_files:
                break
        return "\n".join(files)
