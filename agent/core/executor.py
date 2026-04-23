from __future__ import annotations

from typing import Any, Dict, List, Tuple

from agent.tools.filesystem import FileSystemTool
from agent.tools.git_tools import GitTool
from agent.tools.search import SearchTool
from agent.tools.shell import ShellTool


class Executor:
    TOOL_ARG_RULES: Dict[str, Dict[str, Any]] = {
        "list_files": {"required": [], "allowed": {"path"}},
        "read_file": {"required": ["path"], "allowed": {"path"}},
        "search_code": {"required": ["query"], "allowed": {"query"}},
        "write_file": {"required": ["path", "content"], "allowed": {"path", "content"}},
        "replace_in_file": {"required": ["path", "old", "new"], "allowed": {"path", "old", "new", "count"}},
        "append_file": {"required": ["path", "content"], "allowed": {"path", "content"}},
        "run_command": {"required": ["command"], "allowed": {"command"}},
        "git_status": {"required": [], "allowed": set()},
        "git_diff": {"required": [], "allowed": set()},
    }

    def __init__(
        self,
        filesystem: FileSystemTool,
        search: SearchTool,
        shell: ShellTool,
        git: GitTool,
    ) -> None:
        self.filesystem = filesystem
        self.search = search
        self.shell = shell
        self.git = git

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
                            "path": {"type": "string", "description": "Relative path, default '.'"},
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
                            "path": {"type": "string", "description": "Relative file path to read"},
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
                            "query": {"type": "string", "description": "Text or regex-like query"},
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
                            "command": {"type": "string", "description": "Single shell command to run"},
                        },
                        "required": ["command"],
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

    def _validate_tool_call(self, tool_name: str, args: Dict[str, Any]) -> None:
        if tool_name not in self.TOOL_ARG_RULES:
            raise ValueError(f"Unknown tool: {tool_name}")
        if not isinstance(args, dict):
            raise ValueError(f"Tool args for {tool_name} must be a JSON object")
        rules = self.TOOL_ARG_RULES[tool_name]
        missing = [key for key in rules["required"] if key not in args]
        if missing:
            raise ValueError(f"Missing required args for {tool_name}: {', '.join(missing)}")
        unknown = sorted(set(args) - set(rules["allowed"]))
        if unknown:
            raise ValueError(f"Unknown args for {tool_name}: {', '.join(unknown)}")

    def run_tool(self, tool_name: str, args: Dict[str, Any]) -> Tuple[str, List[str], List[str]]:
        self._validate_tool_call(tool_name, args)
        changed_files: List[str] = []
        commands_run: List[str] = []

        if tool_name == "list_files":
            return "\n".join(self.filesystem.list_files(args.get("path", "."))), changed_files, commands_run
        if tool_name == "read_file":
            return self.filesystem.read_file(args["path"]), changed_files, commands_run
        if tool_name == "search_code":
            return "\n".join(self.search.search_code(args["query"])), changed_files, commands_run
        if tool_name == "write_file":
            changed_path = self.filesystem.write_file(args["path"], args["content"])
            changed_files = [changed_path]
            return f"Wrote file: {changed_path}", changed_files, commands_run
        if tool_name == "replace_in_file":
            changed_path = self.filesystem.replace_in_file(
                args["path"],
                args["old"],
                args["new"],
                count=int(args.get("count", 1)),
            )
            changed_files = [changed_path]
            return f"Updated file: {changed_path}", changed_files, commands_run
        if tool_name == "append_file":
            changed_path = self.filesystem.append_file(args["path"], args["content"])
            changed_files = [changed_path]
            return f"Appended file: {changed_path}", changed_files, commands_run
        if tool_name == "run_command":
            command = args["command"]
            commands_run = [command]
            return self.shell.run_command(command), changed_files, commands_run
        if tool_name == "git_status":
            return self.git.status(), changed_files, commands_run
        if tool_name == "git_diff":
            return self.git.diff(), changed_files, commands_run
        raise ValueError(f"Unknown tool: {tool_name}")
