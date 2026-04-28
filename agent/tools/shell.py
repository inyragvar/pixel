from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


class ShellTool:
    DENYLIST_SUBSTRINGS = {
        "rm -rf /",
        "shutdown",
        "reboot",
        "mkfs",
        ":(){ :|:& };:",
        "dd if=",
        "sudo ",
        "su -",
        "chmod -R 777 /",
        "chown -R",
        "git push",
        "git commit",
    }
    DENYLIST_REGEXES = (
        re.compile(r"\bcurl\b.*\|\s*(?:sh|bash)"),
        re.compile(r"\bwget\b.*\|\s*(?:sh|bash)"),
        re.compile(r"\brm\s+-rf\s+(?:/|~|\$HOME)(?:\s|$)"),
    )

    def __init__(self, workspace: Path, timeout: int = 60, max_output_chars: int = 12_000) -> None:
        self.workspace = workspace.resolve()
        self.timeout = timeout
        self.max_output_chars = max_output_chars

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

    def _validate_command(self, command: str) -> None:
        normalized = command.strip()
        for denied in self.DENYLIST_SUBSTRINGS:
            if denied in normalized:
                raise ValueError(f"Blocked dangerous command pattern: {denied}")
        for pattern in self.DENYLIST_REGEXES:
            if pattern.search(normalized):
                raise ValueError(f"Blocked dangerous command pattern: {pattern.pattern}")

    def run_command(self, command: str) -> str:
        self._validate_command(command)
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
        stdout = result.stdout[-self.max_output_chars :]
        stderr = result.stderr[-self.max_output_chars :]
        return f"exit_code={result.returncode}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
