from __future__ import annotations

from typing import Any, Dict, List, Optional

from openai import OpenAI

from agent.providers.base import Provider


class OpenAICompatibleProvider(Provider):
    def __init__(self, *, base_url: str, api_key: str) -> None:
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def generate(
        self,
        *,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        model: str,
        response_schema: Optional[type] = None,
    ) -> Any:
        input_messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}, *messages]

        if response_schema is not None:
            completion = self.client.beta.chat.completions.parse(
                model=model,
                messages=input_messages,
                response_format=response_schema,
            )
            return completion.choices[0].message.parsed

        completion = self.client.chat.completions.create(
            model=model,
            messages=input_messages,
            temperature=0.2,
        )
        return completion.choices[0].message.content
