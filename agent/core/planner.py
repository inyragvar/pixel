from __future__ import annotations

from agent.schemas.plan import Plan


class Planner:
    def __init__(self, provider, model: str) -> None:
        self.provider = provider
        self.model = model

    def create_plan(self, task: str) -> Plan:
        return self.provider.generate(
            system_prompt="Create a concise implementation plan for the task.",
            messages=[{"role": "user", "content": task}],
            model=self.model,
            response_schema=Plan,
        )
