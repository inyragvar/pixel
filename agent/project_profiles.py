from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Literal

ProjectType = Literal["python", "node", "go", "rust", "unknown"]
ValidationMode = Literal["all", "test", "lint", "typecheck", "build"]


@dataclass
class ProjectProfile:
    project_type: ProjectType
    root: Path
    package_manager: str | None = None
    markers: List[str] = field(default_factory=list)
    commands: dict[str, List[str]] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [f"project_type={self.project_type}"]
        if self.package_manager:
            lines.append(f"package_manager={self.package_manager}")
        if self.markers:
            lines.append(f"markers={', '.join(self.markers)}")
        for mode in ["test", "lint", "typecheck", "build"]:
            cmds = self.commands.get(mode) or []
            if cmds:
                lines.append(f"{mode}={'; '.join(cmds)}")
        return "\n".join(lines)


class ProjectDetector:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()

    def detect(self) -> ProjectProfile:
        root = self.workspace
        markers: List[str] = []

        cargo = root / "Cargo.toml"
        gomod = root / "go.mod"
        package_json = root / "package.json"
        pyproject = root / "pyproject.toml"
        setup_py = root / "setup.py"
        requirements = root / "requirements.txt"

        if cargo.exists():
            markers.append("Cargo.toml")
            return ProjectProfile(
                project_type="rust",
                root=root,
                markers=markers,
                commands={
                    "test": ["cargo test"],
                    "lint": ["cargo clippy --all-targets --all-features -- -D warnings"],
                    "typecheck": ["cargo check"],
                    "build": ["cargo build"],
                },
            )

        if gomod.exists():
            markers.append("go.mod")
            return ProjectProfile(
                project_type="go",
                root=root,
                markers=markers,
                commands={
                    "test": ["go test ./..."],
                    "lint": ["go vet ./..."],
                    "build": ["go build ./..."],
                },
            )

        if package_json.exists():
            markers.append("package.json")
            return self._detect_node_profile(package_json, markers)

        if pyproject.exists() or setup_py.exists() or requirements.exists():
            if pyproject.exists():
                markers.append("pyproject.toml")
            if setup_py.exists():
                markers.append("setup.py")
            if requirements.exists():
                markers.append("requirements.txt")
            return self._detect_python_profile(pyproject if pyproject.exists() else None, markers)

        return ProjectProfile(project_type="unknown", root=root, markers=markers, commands={})

    def _detect_node_profile(self, package_json: Path, markers: List[str]) -> ProjectProfile:
        package_manager = "npm"
        if (self.workspace / "pnpm-lock.yaml").exists():
            package_manager = "pnpm"
            markers.append("pnpm-lock.yaml")
        elif (self.workspace / "yarn.lock").exists():
            package_manager = "yarn"
            markers.append("yarn.lock")
        elif (self.workspace / "package-lock.json").exists():
            package_manager = "npm"
            markers.append("package-lock.json")

        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        scripts = data.get("scripts") or {}

        def script_cmd(name: str) -> List[str]:
            if name not in scripts:
                return []
            if package_manager == "pnpm":
                return [f"pnpm {name}"]
            if package_manager == "yarn":
                return [f"yarn {name}"]
            return [f"npm run {name}"]

        commands = {
            "test": script_cmd("test"),
            "lint": script_cmd("lint"),
            "typecheck": script_cmd("typecheck"),
            "build": script_cmd("build"),
        }
        return ProjectProfile(
            project_type="node",
            root=self.workspace,
            package_manager=package_manager,
            markers=markers,
            commands=commands,
        )

    def _detect_python_profile(self, pyproject: Path | None, markers: List[str]) -> ProjectProfile:
        commands: dict[str, List[str]] = {}
        root = self.workspace
        pyproject_text = ""
        if pyproject is not None:
            try:
                pyproject_text = pyproject.read_text(encoding="utf-8")
            except Exception:
                pyproject_text = ""

        tests_present = (root / "tests").exists() or "pytest" in pyproject_text or (root / "pytest.ini").exists()
        if tests_present:
            commands["test"] = ["python -m pytest -q"]

        lint_cmds: List[str] = []
        if "ruff" in pyproject_text or (root / "ruff.toml").exists() or (root / ".ruff.toml").exists():
            lint_cmds.append("python -m ruff check .")
        commands["lint"] = lint_cmds

        type_cmds: List[str] = []
        if "mypy" in pyproject_text or (root / "mypy.ini").exists() or (root / ".mypy.ini").exists():
            type_cmds.append("python -m mypy .")
        commands["typecheck"] = type_cmds

        build_cmds: List[str] = []
        if pyproject is not None or (root / "setup.py").exists():
            build_cmds.append("python -m compileall .")
        commands["build"] = build_cmds

        return ProjectProfile(project_type="python", root=root, markers=markers, commands=commands)


def commands_for_mode(profile: ProjectProfile, mode: ValidationMode) -> List[str]:
    if mode == "all":
        ordered: List[str] = []
        for key in ["lint", "typecheck", "test", "build"]:
            ordered.extend(profile.commands.get(key, []))
        return ordered
    return list(profile.commands.get(mode, []))
