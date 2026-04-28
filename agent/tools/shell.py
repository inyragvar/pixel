from __future__ import annotations

import os
import shlex
import shutil
import sys
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

    def _resolve_command(self, command: str) -> str:
      normalized = command.strip()
      if not normalized:
          return normalized

      parts = shlex.split(normalized, posix=True)
      if not parts:
          return normalized

      if parts[0] == "python":
          python_bin = shutil.which("python") or sys.executable or shutil.which("python3") or "python"
          parts[0] = python_bin
          return shlex.join(parts)

      return normalized

    def run_command(self, command: str) -> str:
        normalized = command.strip()
        for denied in self.DENYLIST:
            if denied in normalized:
                raise ValueError(f"Blocked dangerous command pattern: {denied}")

        shell_command = self._resolve_command(command)
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
