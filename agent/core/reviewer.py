from __future__ import annotations

from agent.schemas.outputs import FinalAnswer


class Reviewer:
    def __init__(self, provider, model: str) -> None:
        self.provider = provider
        self.model = model

    def summarize(self, task: str, transcript: str) -> FinalAnswer:
        return self.provider.generate(
            system_prompt="Summarize the work completed for the task. Be honest about gaps.",
            messages=[
                {"role": "user", "content": f"Task:\n{task}\n\nTranscript:\n{transcript}"}
            ],
            model=self.model,
            response_schema=FinalAnswer,
        )
