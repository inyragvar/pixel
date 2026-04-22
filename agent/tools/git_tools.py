from __future__ import annotations

import subprocess
from pathlib import Path


class GitTool:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

    def _run(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.workspace,
            text=True,
            capture_output=True,
            check=False,
        )
        return (result.stdout + "\n" + result.stderr).strip()

    def status(self) -> str:
        return self._run("status", "--short")

    def diff(self) -> str:
        return self._run("diff", "--", ".")
