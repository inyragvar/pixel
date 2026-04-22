from __future__ import annotations

from typing import Any, Dict, List, Tuple

from agent.tools.filesystem import FileSystemTool
from agent.tools.git_tools import GitTool
from agent.tools.search import SearchTool
from agent.tools.shell import ShellTool


class Executor:
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
        return [
            "list_files(path='.')",
            "read_file(path)",
            "search_code(query)",
            "write_file(path, content)",
            "replace_in_file(path, old, new, count=1)",
            "append_file(path, content)",
            "run_command(command)",
            "git_status()",
            "git_diff()",
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
        if tool == "git_status":
            return self.git.status(), changed_files, commands_run
        if tool == "git_diff":
            return self.git.diff(), changed_files, commands_run
        raise ValueError(f"Unknown tool: {tool}")
