from __future__ import annotations

from typing import Any, Dict, List, Tuple

from agent.tools.filesystem import FileSystemTool
from agent.tools.git_tools import GitTool
from agent.tools.search import SearchTool
from agent.tools.shell import ShellTool
from agent.tools.validation import ValidationTool


class Executor:
    def __init__(
        self,
        filesystem: FileSystemTool,
        search: SearchTool,
        shell: ShellTool,
        git: GitTool,
        validation: ValidationTool,
    ) -> None:
        self.filesystem = filesystem
        self.search = search
        self.shell = shell
        self.git = git
        self.validation = validation

    def available_tools(self) -> List[str]:
        return [tool["function"]["name"] for tool in self.tool_schemas()]

    def tool_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "List files under a path relative to the workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Relative path, default '.'"}
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a UTF-8 text file from the workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Relative file path to read"}
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_code",
                    "description": "Search code or text in the workspace with ripgrep-like matching.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Text or regex-like query"}
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file, creating or replacing it.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "replace_in_file",
                    "description": "Replace text in a file for targeted edits.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "old": {"type": "string"},
                            "new": {"type": "string"},
                            "count": {"type": "integer", "minimum": 1},
                        },
                        "required": ["path", "old", "new"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "append_file",
                    "description": "Append content to the end of a file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_command",
                    "description": "Run a safe workspace-local shell command for validation or inspection.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Single shell command to run"}
                        },
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "detect_project",
                    "description": "Detect the project type and available validation commands for the current workspace.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_validation",
                    "description": "Run sensible validation commands automatically for the detected project. Modes: all, test, lint, typecheck, build.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "mode": {"type": "string", "enum": ["all", "test", "lint", "typecheck", "build"]}
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "git_status",
                    "description": "Show git status for the workspace.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "git_diff",
                    "description": "Show git diff for the workspace.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

    def run_tool(self, tool: str, args: Dict[str, Any]) -> Tuple[str, List[str], List[str]]:
        changed_files: List[str] = []
        commands_run: List[str] = []

        if tool == "list_files":
            return "\n".join(self.filesystem.list_files(args.get("path", "."))), changed_files, commands_run
        if tool == "read_file":
            return self.filesystem.read_file(args["path"]), changed_files, commands_run
        if tool == "search_code":
            return "\n".join(self.search.search_code(args["query"])), changed_files, commands_run
        if tool == "write_file":
            changed_files = [self.filesystem.write_file(args["path"], args["content"])]
            return f"Wrote file: {changed_files[0]}", changed_files, commands_run
        if tool == "replace_in_file":
            changed_files = [
                self.filesystem.replace_in_file(
                    args["path"],
                    args["old"],
                    args["new"],
                    count=int(args.get("count", 1)),
                )
            ]
            return f"Updated file: {changed_files[0]}", changed_files, commands_run
        if tool == "append_file":
            changed_files = [self.filesystem.append_file(args["path"], args["content"])]
            return f"Appended file: {changed_files[0]}", changed_files, commands_run
        if tool == "run_command":
            command = args["command"]
            commands_run = [command]
            return self.shell.run_command(command), changed_files, commands_run
        if tool == "detect_project":
            return self.validation.detect_project(), changed_files, commands_run
        if tool == "run_validation":
            mode = str(args.get("mode", "all"))
            result = self.validation.run_validation(mode)
            commands_run = [line[2:] for line in result.splitlines() if line.startswith("$ ")]
            return result, changed_files, commands_run
        if tool == "git_status":
            return self.git.status(), changed_files, commands_run
        if tool == "git_diff":
            return self.git.diff(), changed_files, commands_run
        raise ValueError(f"Unknown tool: {tool}")
