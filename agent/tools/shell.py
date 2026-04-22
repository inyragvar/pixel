from __future__ import annotations

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

        subprocess.run(["bash", "-lc", f"cd {shlex.quote(str(self.workspace))}"], check=False)
        result = subprocess.run(
            ["bash", "-lc", command],
            cwd=self.workspace,
            text=True,
            capture_output=True,
            timeout=self.timeout,
            check=False,
        )
        stdout = result.stdout[-12000:]
        stderr = result.stderr[-12000:]
        return f"exit_code={result.returncode}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
