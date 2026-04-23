from __future__ import annotations

import json
from pathlib import Path

from agent.project_profiles import ProjectDetector, commands_for_mode
from agent.tools.shell import ShellTool
from agent.tools.validation import ValidationTool


def test_detect_python_profile(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """[project]
name = "x"
[tool.ruff]
[tool.mypy]
""",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()

    profile = ProjectDetector(tmp_path).detect()

    assert profile.project_type == "python"
    assert "python -m pytest -q" in commands_for_mode(profile, "test")
    assert "python -m ruff check ." in commands_for_mode(profile, "lint")
    assert "python -m mypy ." in commands_for_mode(profile, "typecheck")


def test_detect_node_profile_from_package_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "name": "x",
                "scripts": {"test": "vitest", "lint": "eslint .", "build": "tsc -b"},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: 9", encoding="utf-8")

    profile = ProjectDetector(tmp_path).detect()

    assert profile.project_type == "node"
    assert profile.package_manager == "pnpm"
    assert commands_for_mode(profile, "test") == ["pnpm test"]
    assert commands_for_mode(profile, "build") == ["pnpm build"]


def test_detect_go_and_rust_profiles(tmp_path: Path) -> None:
    go_root = tmp_path / "go_proj"
    go_root.mkdir()
    (go_root / "go.mod").write_text("module example.com/x\n", encoding="utf-8")
    rust_root = tmp_path / "rust_proj"
    rust_root.mkdir()
    (rust_root / "Cargo.toml").write_text(
        """[package]
name = "x"
version = "0.1.0"
""",
        encoding="utf-8",
    )

    go_profile = ProjectDetector(go_root).detect()
    rust_profile = ProjectDetector(rust_root).detect()

    assert go_profile.project_type == "go"
    assert commands_for_mode(go_profile, "test") == ["go test ./..."]
    assert rust_profile.project_type == "rust"
    assert "cargo check" in commands_for_mode(rust_profile, "typecheck")


def test_validation_tool_runs_detected_python_command(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """[project]
name = "x"
""",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_ok.py").write_text(
        """def test_ok():
    assert 1 == 1
""",
        encoding="utf-8",
    )

    tool = ValidationTool(tmp_path, ShellTool(tmp_path, timeout=30))
    output = tool.run_validation("test")

    assert "project_type=python" in output
    assert "$ python -m pytest -q" in output
    assert "exit_code=0" in output
