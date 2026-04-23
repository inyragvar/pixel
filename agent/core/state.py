from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AgentState:
    task: str
    notes: List[str] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)
    commands_run: List[str] = field(default_factory=list)
    changed_files: List[str] = field(default_factory=list)
    history: List[str] = field(default_factory=list)
    step_count: int = 0
    finished: bool = False
    artifact_dir: Optional[str] = None
    run_id: Optional[str] = None
