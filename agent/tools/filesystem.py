from __future__ import annotations

from pathlib import Path
from typing import List


class FileSystemTool:
    def __init__(
        self,
        workspace: Path,
        *,
        max_read_bytes: int = 200_000,
        max_write_bytes: int = 500_000,
    ) -> None:
        self.workspace = workspace.resolve()
        self.max_read_bytes = max_read_bytes
        self.max_write_bytes = max_write_bytes

    def _resolve(self, path: str) -> Path:
        candidate = (self.workspace / path).resolve()
        if self.workspace not in [candidate, *candidate.parents]:
            raise ValueError("Path escapes workspace")
        return candidate

    def _ensure_text_file(self, target: Path) -> None:
        if target.exists() and not target.is_file():
            raise ValueError("Path is not a regular file")
        if target.exists() and target.stat().st_size > self.max_read_bytes:
            raise ValueError(f"File too large to operate on safely: {target}")

    def list_files(self, path: str = ".") -> List[str]:
        root = self._resolve(path)
        if not root.exists():
            return []
        return sorted(
            str(p.relative_to(self.workspace))
            for p in root.rglob("*")
            if p.is_file() and ".git" not in p.parts
        )[:1000]

    def read_file(self, path: str) -> str:
        target = self._resolve(path)
        self._ensure_text_file(target)
        return target.read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> str:
        encoded = content.encode("utf-8")
        if len(encoded) > self.max_write_bytes:
            raise ValueError("Write content too large")
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target.relative_to(self.workspace))

    def append_file(self, path: str, content: str) -> str:
        encoded = content.encode("utf-8")
        if len(encoded) > self.max_write_bytes:
            raise ValueError("Append content too large")
        target = self._resolve(path)
        self._ensure_text_file(target) if target.exists() else None
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(content)
        return str(target.relative_to(self.workspace))

    def replace_in_file(self, path: str, old: str, new: str, *, count: int = 1) -> str:
        if len(new.encode("utf-8")) > self.max_write_bytes:
            raise ValueError("Replacement content too large")
        target = self._resolve(path)
        self._ensure_text_file(target)
        content = target.read_text(encoding="utf-8")
        if old not in content:
            raise ValueError(f"Text to replace not found in {path}")
        updated = content.replace(old, new, count)
        target.write_text(updated, encoding="utf-8")
        return str(target.relative_to(self.workspace))
