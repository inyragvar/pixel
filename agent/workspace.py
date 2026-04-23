from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List


DEFAULT_COPY_EXCLUDES: List[str] = [
    ".venv",
    "venv",
    "env",
    "ENV",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".hypothesis",
    ".tox",
    ".nox",
    "node_modules",
    "dist",
    "build",
    "site",
    "htmlcov",
    ".coverage",
    "artifacts",
    "runs",
    "tmp",
    ".cache",
]


@dataclass
class IsolatedWorkspace:
    source_path: Path
    root_path: Path
    mode: str = "copy"
    keep: bool = False

    def cleanup(self) -> None:
        if self.keep:
            return
        if self.root_path.exists() and self.root_path != self.source_path:
            shutil.rmtree(self.root_path, ignore_errors=True)


class WorkspaceManager:
    def __init__(
        self,
        source_workspace: Path,
        *,
        enabled: bool = True,
        keep_isolated: bool = False,
        base_dir: Path | None = None,
        exclude_names: List[str] | None = None,
    ) -> None:
        self.source_workspace = source_workspace.resolve()
        self.enabled = enabled
        self.keep_isolated = keep_isolated
        self.base_dir = base_dir.resolve() if base_dir else None
        self.exclude_names = set(exclude_names or DEFAULT_COPY_EXCLUDES)

    def _ignore(self, directory: str, names: List[str]) -> List[str]:
        ignored: List[str] = []
        for name in names:
            if name in self.exclude_names:
                ignored.append(name)
        return ignored

    def prepare(self) -> IsolatedWorkspace:
        if not self.enabled:
            return IsolatedWorkspace(
                source_path=self.source_workspace,
                root_path=self.source_workspace,
                mode="live",
                keep=True,
            )

        parent = self.base_dir
        if parent is not None:
            parent.mkdir(parents=True, exist_ok=True)
            temp_dir = Path(
                tempfile.mkdtemp(prefix="dev-agent-run-", dir=str(parent))
            ).resolve()
        else:
            temp_dir = Path(tempfile.mkdtemp(prefix="dev-agent-run-")).resolve()

        destination = temp_dir / self.source_workspace.name
        shutil.copytree(
            self.source_workspace,
            destination,
            dirs_exist_ok=False,
            ignore=self._ignore,
        )
        return IsolatedWorkspace(
            source_path=self.source_workspace,
            root_path=destination,
            mode="copy",
            keep=self.keep_isolated,
        )
