from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

DEFAULT_ALLOWLIST_PATTERNS: tuple[str, ...] = ("*",)
DEFAULT_DENYLIST_PATTERNS: tuple[str, ...] = (
    ".git/*",
    ".venv/*",
    "venv/*",
    "env/*",
    "node_modules/*",
    "dist/*",
    "build/*",
    "__pycache__/*",
    ".pytest_cache/*",
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.dll",
    "*.dylib",
    "*.exe",
    "*.bin",
    "*.jpg",
    "*.jpeg",
    "*.png",
    "*.gif",
    "*.webp",
    "*.pdf",
)


class FileSystemTool:
    def __init__(
        self,
        workspace: Path,
        *,
        allowlist_patterns: Iterable[str] = DEFAULT_ALLOWLIST_PATTERNS,
        denylist_patterns: Iterable[str] = DEFAULT_DENYLIST_PATTERNS,
    ) -> None:
        self.workspace = workspace.resolve()
        self.allowlist_patterns = tuple(allowlist_patterns)
        self.denylist_patterns = tuple(denylist_patterns)

    def _resolve(self, path: str) -> Path:
        candidate = (self.workspace / path).resolve()
        if self.workspace not in [candidate, *candidate.parents]:
            raise ValueError("Path escapes workspace")
        self._ensure_safe(candidate)
        return candidate

    def _relative_path(self, candidate: Path) -> str:
        return str(candidate.relative_to(self.workspace)).replace('\\', '/')

    def _is_denied(self, candidate: Path) -> bool:
        rel = self._relative_path(candidate)
        if rel in {'.', ''}:
            return False
        return any(candidate.match(pattern) or Path(rel).match(pattern) for pattern in self.denylist_patterns)

    def _is_allowed(self, candidate: Path) -> bool:
        rel = self._relative_path(candidate)
        if rel in {'.', ''}:
            return True
        return any(candidate.match(pattern) or Path(rel).match(pattern) for pattern in self.allowlist_patterns)

    def _ensure_safe(self, candidate: Path) -> None:
        if not self._is_allowed(candidate):
            raise ValueError(f"Path is not allowed: {self._relative_path(candidate)}")
        if self._is_denied(candidate):
            raise ValueError(f"Path is denied: {self._relative_path(candidate)}")

    def list_files(self, path: str = ".") -> List[str]:
        root = self._resolve(path)
        if not root.exists():
            return []
        return sorted(
            self._relative_path(p)
            for p in root.rglob("*")
            if p.is_file() and ".git" not in p.parts and self._is_allowed(p) and not self._is_denied(p)
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
