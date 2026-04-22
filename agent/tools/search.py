from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List


class SearchTool:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

    def search_code(self, query: str) -> List[str]:
        cmd = ["rg", "-n", "--hidden", "--glob", "!.git", query, str(self.workspace)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            raise RuntimeError("ripgrep (rg) is required for search_code")

        lines = [line for line in result.stdout.splitlines() if line.strip()]
        return lines[:200]
