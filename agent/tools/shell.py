from __future__ import annotations

import os
import shlex
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
        normalized = command.strip()
        for denied in self.DENYLIST:
            if denied in normalized:
                raise ValueError(f"Blocked dangerous command pattern: {denied}")

        bootstrap = (
            "if ! command -v python >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then "
            "alias python=python3; "
            "fi; "
        )
        shell_command = bootstrap + command
        env = os.environ.copy()
        result = subprocess.run(
            ["bash", "-lc", shell_command],
            cwd=self.workspace,
            text=True,
            capture_output=True,
            timeout=self.timeout,
            check=False,
            env=env,
        )
        stdout = result.stdout[-12000:]
        stderr = result.stderr[-12000:]
        return f"exit_code={result.returncode}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
