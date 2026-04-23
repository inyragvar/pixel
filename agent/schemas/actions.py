from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ToolAction(BaseModel):
    tool: Literal[
        "list_files",
        "read_file",
        "search_code",
        "write_file",
        "replace_in_file",
        "append_file",
        "run_command",
        "detect_project",
        "run_validation",
        "git_status",
        "git_diff",
    ]
    args: Dict[str, Any] = Field(default_factory=dict)
    reasoning: Optional[str] = None


class AgentDecision(BaseModel):
    decision: Literal["tool", "final"]
    tool: Optional[ToolAction] = None
    summary: Optional[str] = None
    next_steps: List[str] = Field(default_factory=list)
    changed_files: List[str] = Field(default_factory=list)
    reasoning: Optional[str] = None
