from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    id: str = Field(description="Stable step identifier")
    title: str
    description: str


class Plan(BaseModel):
    summary: str
    steps: List[PlanStep]
    risks: List[str] = []
