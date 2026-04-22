from __future__ import annotations

from pathlib import Path
from typing import List


class FileSystemTool:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()

    def _resolve(self, path: str) -> Path:
        candidate = (self.workspace / path).resolve()
        if self.workspace not in [candidate, *candidate.parents]:
            raise ValueError("Path escapes workspace")
        return candidate

    def list_files(self, path: str = ".") -> List[str]:
        root = self._resolve(path)
        if not root.exists():
            return []
        return sorted(
            str(p.relative_to(self.workspace))
            for p in root.rglob("*")
            if p.is_file() and ".git" not in p.parts
        )

    def read_file(self, path: str) -> str:
        return self._resolve(path).read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> str:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target.relative_to(self.workspace))

    def append_file(self, path: str, content: str) -> str:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(content)
        return str(target.relative_to(self.workspace))

    def replace_in_file(self, path: str, old: str, new: str, *, count: int = 1) -> str:
        target = self._resolve(path)
        content = target.read_text(encoding="utf-8")
        if old not in content:
            raise ValueError(f"Text to replace not found in {path}")
        updated = content.replace(old, new, count)
        target.write_text(updated, encoding="utf-8")
        return str(target.relative_to(self.workspace))
