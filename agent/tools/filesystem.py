from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


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
        self._original_contents: Dict[str, Optional[str]] = {}

    def _resolve(self, path: str) -> Path:
        candidate = (self.workspace / path).resolve()
        if self.workspace not in [candidate, *candidate.parents]:
            raise ValueError("Path escapes workspace")
        return candidate

    def _rel(self, target: Path) -> str:
        return str(target.relative_to(self.workspace))

    def _ensure_text_file(self, target: Path) -> None:
        if target.exists() and not target.is_file():
            raise ValueError("Path is not a regular file")
        if target.exists() and target.stat().st_size > self.max_read_bytes:
            raise ValueError(f"File too large to operate on safely: {target}")

    def _check_write_size(self, content: str) -> None:
        if len(content.encode("utf-8")) > self.max_write_bytes:
            raise ValueError("Write content too large")

    def _record_original(self, target: Path) -> None:
        rel = self._rel(target)
        if rel in self._original_contents:
            return
        if target.exists():
            self._ensure_text_file(target)
            self._original_contents[rel] = target.read_text(encoding="utf-8")
        else:
            self._original_contents[rel] = None

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
        self._check_write_size(content)
        target = self._resolve(path)
        self._record_original(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return self._rel(target)

    def append_file(self, path: str, content: str) -> str:
        self._check_write_size(content)
        target = self._resolve(path)
        self._record_original(target)
        self._ensure_text_file(target) if target.exists() else None
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(content)
        return self._rel(target)

    def replace_in_file(self, path: str, old: str, new: str, *, count: int = 1) -> str:
        target = self._resolve(path)
        self._ensure_text_file(target)
        content = target.read_text(encoding="utf-8")
        if old not in content:
            raise ValueError(f"Text to replace not found in {path}")
        updated = content.replace(old, new, count)
        self._check_write_size(updated)
        self._record_original(target)
        target.write_text(updated, encoding="utf-8")
        return self._rel(target)

    def _strip_diff_prefix(self, value: str) -> str:
        if value.startswith("a/") or value.startswith("b/"):
            return value[2:]
        return value

    def _parse_unified_patch(self, patch: str) -> List[Dict[str, object]]:
        lines = patch.splitlines()
        files: List[Dict[str, object]] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if not line.startswith("--- "):
                i += 1
                continue
            if i + 1 >= len(lines) or not lines[i + 1].startswith("+++ "):
                raise ValueError("Invalid unified diff: missing +++ line")
            old_raw = lines[i][4:].split("\t", 1)[0].strip()
            new_raw = lines[i + 1][4:].split("\t", 1)[0].strip()
            old_path = None if old_raw == "/dev/null" else self._strip_diff_prefix(old_raw)
            new_path = None if new_raw == "/dev/null" else self._strip_diff_prefix(new_raw)
            hunks: List[str] = []
            i += 2
            while i < len(lines) and not lines[i].startswith("--- "):
                hunks.append(lines[i])
                i += 1
            files.append({"old_path": old_path, "new_path": new_path, "hunks": hunks})
        if not files:
            raise ValueError("No unified diff file sections found")
        return files

    def _apply_hunks(self, original: List[str], hunk_lines: List[str], path: str) -> List[str]:
        result: List[str] = []
        orig_index = 0
        i = 0
        header_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
        while i < len(hunk_lines):
            header = hunk_lines[i]
            if not header.startswith("@@"):
                if header.startswith("\\ No newline at end of file"):
                    i += 1
                    continue
                raise ValueError(f"Invalid unified diff hunk header in {path}: {header}")
            match = header_re.match(header)
            if not match:
                raise ValueError(f"Malformed unified diff hunk header in {path}: {header}")
            old_start = int(match.group(1))
            target_index = max(old_start - 1, 0)
            if target_index < orig_index:
                raise ValueError(f"Overlapping hunks are not supported in {path}")
            result.extend(original[orig_index:target_index])
            orig_index = target_index
            i += 1
            while i < len(hunk_lines) and not hunk_lines[i].startswith("@@"):
                line = hunk_lines[i]
                if line.startswith("\\ No newline at end of file"):
                    i += 1
                    continue
                if not line:
                    prefix, text = " ", ""
                else:
                    prefix, text = line[0], line[1:]
                if prefix == " ":
                    if orig_index >= len(original) or original[orig_index] != text:
                        raise ValueError(f"Context mismatch while applying patch to {path}")
                    result.append(text)
                    orig_index += 1
                elif prefix == "-":
                    if orig_index >= len(original) or original[orig_index] != text:
                        raise ValueError(f"Removal mismatch while applying patch to {path}")
                    orig_index += 1
                elif prefix == "+":
                    result.append(text)
                else:
                    raise ValueError(f"Unsupported diff line prefix '{prefix}' in {path}")
                i += 1
        result.extend(original[orig_index:])
        return result

    def apply_patch(self, patch: str) -> List[str]:
        files = self._parse_unified_patch(patch)
        changed: List[str] = []
        for file_patch in files:
            old_path = file_patch["old_path"]
            new_path = file_patch["new_path"]
            hunks = file_patch["hunks"]
            target_path = new_path or old_path
            if target_path is None:
                raise ValueError("Patch file section has no target path")
            target = self._resolve(str(target_path))
            existing_content: Optional[str]
            if old_path is None:
                existing_content = None
            else:
                existing_target = self._resolve(str(old_path))
                if existing_target.exists():
                    self._ensure_text_file(existing_target)
                    existing_content = existing_target.read_text(encoding="utf-8")
                else:
                    raise ValueError(f"Patch references missing file: {old_path}")
            self._record_original(target)
            original_lines = [] if existing_content is None else existing_content.splitlines()
            updated_lines = self._apply_hunks(original_lines, list(hunks), str(target_path))
            updated_content = "\n".join(updated_lines)
            if existing_content is not None and existing_content.endswith("\n"):
                updated_content += "\n"
            if new_path is None:
                if target.exists():
                    target.unlink()
                changed.append(self._rel(target))
                continue
            self._check_write_size(updated_content)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(updated_content, encoding="utf-8")
            changed.append(self._rel(target))
        return sorted(set(changed))

    def rollback_file(self, path: str) -> str:
        target = self._resolve(path)
        rel = self._rel(target)
        if rel not in self._original_contents:
            raise ValueError(f"No tracked original state for {path}")
        original = self._original_contents.pop(rel)
        if original is None:
            if target.exists():
                target.unlink()
            return rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(original, encoding="utf-8")
        return rel

    def rollback_all(self) -> List[str]:
        changed = sorted(self._original_contents)
        for rel in list(changed):
            self.rollback_file(rel)
        return changed

    def tracked_changes(self) -> List[str]:
        return sorted(self._original_contents)
