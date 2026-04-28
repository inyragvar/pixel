from __future__ import annotations

from dataclasses import dataclass
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

DEFAULT_MAX_READ_BYTES = 512_000
DEFAULT_MAX_WRITE_BYTES = 1_000_000
DEFAULT_MAX_LIST_FILES = 2_000


@dataclass(frozen=True)
class _PatchFile:
    old_path: str | None
    new_path: str | None
    hunks: list[list[str]]


class FileSystemTool:
    def __init__(
        self,
        workspace: Path,
        *,
        allowlist_patterns: Iterable[str] = DEFAULT_ALLOWLIST_PATTERNS,
        denylist_patterns: Iterable[str] = DEFAULT_DENYLIST_PATTERNS,
        max_read_bytes: int = DEFAULT_MAX_READ_BYTES,
        max_write_bytes: int = DEFAULT_MAX_WRITE_BYTES,
        max_list_files: int = DEFAULT_MAX_LIST_FILES,
    ) -> None:
        self.workspace = workspace.resolve()
        self.allowlist_patterns = tuple(allowlist_patterns)
        self.denylist_patterns = tuple(denylist_patterns)
        self.max_read_bytes = max_read_bytes
        self.max_write_bytes = max_write_bytes
        self.max_list_files = max_list_files

    def _resolve(self, path: str) -> Path:
        candidate = (self.workspace / path).resolve()
        if self.workspace not in [candidate, *candidate.parents]:
            raise ValueError("Path escapes workspace")
        self._ensure_safe(candidate)
        return candidate

    def _relative_path(self, candidate: Path) -> str:
        return str(candidate.relative_to(self.workspace)).replace("\\", "/")

    def _is_denied(self, candidate: Path) -> bool:
        rel = self._relative_path(candidate)
        if rel in {".", ""}:
            return False
        return any(candidate.match(pattern) or Path(rel).match(pattern) for pattern in self.denylist_patterns)

    def _is_allowed(self, candidate: Path) -> bool:
        rel = self._relative_path(candidate)
        if rel in {".", ""}:
            return True
        return any(candidate.match(pattern) or Path(rel).match(pattern) for pattern in self.allowlist_patterns)

    def _ensure_safe(self, candidate: Path) -> None:
        if not self._is_allowed(candidate):
            raise ValueError(f"Path is not allowed: {self._relative_path(candidate)}")
        if self._is_denied(candidate):
            raise ValueError(f"Path is denied: {self._relative_path(candidate)}")

    @staticmethod
    def _is_binary_bytes(data: bytes) -> bool:
        return b"\x00" in data

    def _ensure_text_file(self, target: Path) -> None:
        if not target.exists() or not target.is_file():
            return
        size = target.stat().st_size
        if size > self.max_read_bytes:
            raise ValueError(f"File is too large to read/edit safely: {self._relative_path(target)} ({size} bytes)")
        with target.open("rb") as fh:
            sample = fh.read(4096)
        if self._is_binary_bytes(sample):
            raise ValueError(f"Refusing to edit binary file: {self._relative_path(target)}")

    def _ensure_write_size(self, content: str) -> None:
        size = len(content.encode("utf-8"))
        if size > self.max_write_bytes:
            raise ValueError(f"Content is too large to write safely: {size} bytes")

    def list_files(self, path: str = ".") -> List[str]:
        root = self._resolve(path)
        if not root.exists():
            return []
        files = sorted(
            self._relative_path(p)
            for p in root.rglob("*")
            if p.is_file() and ".git" not in p.parts and self._is_allowed(p) and not self._is_denied(p)
        )
        return files[: self.max_list_files]

    def read_file(self, path: str) -> str:
        target = self._resolve(path)
        self._ensure_text_file(target)
        return target.read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> str:
        self._ensure_write_size(content)
        target = self._resolve(path)
        self._ensure_text_file(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return self._relative_path(target)

    def append_file(self, path: str, content: str) -> str:
        self._ensure_write_size(content)
        target = self._resolve(path)
        self._ensure_text_file(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(content)
        return self._relative_path(target)

    def replace_in_file(self, path: str, old: str, new: str, *, count: int = 1) -> str:
        target = self._resolve(path)
        self._ensure_text_file(target)
        content = target.read_text(encoding="utf-8")
        if old not in content:
            raise ValueError(f"Text to replace not found in {path}")
        updated = content.replace(old, new, count)
        self._ensure_write_size(updated)
        target.write_text(updated, encoding="utf-8")
        return self._relative_path(target)

    @staticmethod
    def _clean_patch_path(path: str) -> str | None:
        path = path.strip()
        if path == "/dev/null":
            return None
        # Drop timestamps after the path when present in unified diffs.
        path = path.split("\t", 1)[0].split("  ", 1)[0]
        if path.startswith("a/") or path.startswith("b/"):
            path = path[2:]
        return path

    def _parse_unified_diff(self, patch: str) -> list[_PatchFile]:
        lines = patch.splitlines(keepends=True)
        files: list[_PatchFile] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("diff --git "):
                i += 1
                continue
            if not line.startswith("--- "):
                i += 1
                continue

            old_path = self._clean_patch_path(line[4:])
            i += 1
            if i >= len(lines) or not lines[i].startswith("+++ "):
                raise ValueError("Invalid unified diff: expected +++ after ---")
            new_path = self._clean_patch_path(lines[i][4:])
            i += 1

            hunks: list[list[str]] = []
            while i < len(lines):
                if lines[i].startswith("diff --git ") or lines[i].startswith("--- "):
                    break
                if not lines[i].startswith("@@ "):
                    i += 1
                    continue
                hunk = [lines[i]]
                i += 1
                while i < len(lines):
                    hunk_line = lines[i]
                    if hunk_line.startswith("@@ ") or hunk_line.startswith("diff --git ") or hunk_line.startswith("--- "):
                        break
                    if hunk_line.startswith((" ", "+", "-", "\\")):
                        hunk.append(hunk_line)
                    else:
                        raise ValueError(f"Invalid unified diff hunk line: {hunk_line.rstrip()}")
                    i += 1
                hunks.append(hunk)

            if not hunks:
                raise ValueError("Invalid unified diff: file section has no hunks")
            files.append(_PatchFile(old_path=old_path, new_path=new_path, hunks=hunks))

        if not files:
            raise ValueError("No unified diff file sections found")
        return files

    @staticmethod
    def _parse_hunk_header(header: str) -> tuple[int, int]:
        # Example: @@ -3,7 +3,8 @@ optional section
        parts = header.split()
        if len(parts) < 3 or not parts[1].startswith("-") or not parts[2].startswith("+"):
            raise ValueError(f"Invalid hunk header: {header.rstrip()}")
        old_range = parts[1][1:]
        old_start_text, _, old_count_text = old_range.partition(",")
        old_start = int(old_start_text)
        old_count = int(old_count_text or "1")
        return old_start, old_count

    def _apply_hunks_to_text(self, original: str, hunks: list[list[str]], path: str) -> str:
        source_lines = original.splitlines(keepends=True)
        output: list[str] = []
        cursor = 0

        for hunk in hunks:
            old_start, _old_count = self._parse_hunk_header(hunk[0])
            hunk_start = max(old_start - 1, 0)
            if hunk_start < cursor:
                raise ValueError(f"Overlapping or out-of-order hunk for {path}")
            output.extend(source_lines[cursor:hunk_start])
            cursor = hunk_start

            for raw_line in hunk[1:]:
                if raw_line.startswith("\\"):
                    continue
                marker = raw_line[:1]
                value = raw_line[1:]
                if marker == " ":
                    if cursor >= len(source_lines) or source_lines[cursor] != value:
                        raise ValueError(f"Patch context mismatch in {path}: {value.rstrip()}")
                    output.append(source_lines[cursor])
                    cursor += 1
                elif marker == "-":
                    if cursor >= len(source_lines) or source_lines[cursor] != value:
                        raise ValueError(f"Patch removal mismatch in {path}: {value.rstrip()}")
                    cursor += 1
                elif marker == "+":
                    output.append(value)
                else:
                    raise ValueError(f"Unsupported hunk marker in {path}: {marker}")

        output.extend(source_lines[cursor:])
        return "".join(output)

    def apply_patch(self, patch: str) -> list[str]:
        changed: list[str] = []
        for patch_file in self._parse_unified_diff(patch):
            target_path = patch_file.new_path or patch_file.old_path
            if target_path is None:
                raise ValueError("Patch file section has neither old nor new path")
            target = self._resolve(target_path)

            if patch_file.old_path is None:
                original = ""
            else:
                self._ensure_text_file(target)
                original = target.read_text(encoding="utf-8") if target.exists() else ""

            updated = self._apply_hunks_to_text(original, patch_file.hunks, target_path)
            self._ensure_write_size(updated)

            if patch_file.new_path is None:
                if target.exists():
                    target.unlink()
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(updated, encoding="utf-8")
            changed.append(self._relative_path(target))
        return changed
