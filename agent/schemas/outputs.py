from __future__ import annotations

from typing import List

from pydantic import BaseModel


class FinalAnswer(BaseModel):
    summary: str
    changed_files: List[str] = []
    commands_run: List[str] = []
    next_steps: List[str] = []
