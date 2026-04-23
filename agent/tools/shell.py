from __future__ import annotations

import subprocess
from pathlib import Path


class ShellTool:
    DENYLIST = {
        "rm -rf /",
        "shutdown",
        "reboot",
        "mkfs",
        ":(){ :|:& };:",
        "dd if=",
    }

    def __init__(self, workspace: Path, timeout: int = 60) -> None:
        self.workspace = workspace
        self.timeout = timeout

    def run_command(self, command: str) -> str:
        normalized = " ".join(command.strip().split())
        for denied in self.DENYLIST:
            if denied in normalized:
                raise ValueError(f"Blocked dangerous command pattern: {denied}")

        result = subprocess.run(
            ["bash", "-lc", command],
            cwd=self.workspace,
            text=True,
            capture_output=True,
            timeout=self.timeout,
            check=False,
        )
        stdout = result.stdout[-12000:].strip()
        stderr = result.stderr[-12000:].strip()
        return f"exit_code={result.returncode}\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
