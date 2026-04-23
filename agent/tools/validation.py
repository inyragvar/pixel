from __future__ import annotations

from pathlib import Path
from typing import List

from agent.project_profiles import ProjectDetector, commands_for_mode
from agent.tools.shell import ShellTool


class ValidationTool:
    def __init__(self, workspace: Path, shell: ShellTool) -> None:
        self.workspace = workspace.resolve()
        self.shell = shell
        self.detector = ProjectDetector(self.workspace)

    def detect_project(self) -> str:
        profile = self.detector.detect()
        return profile.summary()

    def run_validation(self, mode: str = "all") -> str:
        profile = self.detector.detect()
        commands = commands_for_mode(profile, mode)
        if not commands:
            return (
                f"No validation commands available for project_type={profile.project_type} and mode={mode}.\n"
                f"Detected markers: {', '.join(profile.markers) if profile.markers else 'none'}"
            )

        outputs: List[str] = [profile.summary(), "", f"validation_mode={mode}"]
        for command in commands:
            outputs.append(f"\n$ {command}")
            outputs.append(self.shell.run_command(command))
        return "\n".join(outputs).strip() + "\n"
