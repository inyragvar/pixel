from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ValidationError

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from agent.providers.base import Provider
from agent.providers.capabilities import ProviderCapabilities


class OpenAICompatibleProvider(Provider):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        client: Any | None = None,
        provider_name: str = "openai-compatible",
        capabilities: ProviderCapabilities | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.capabilities = capabilities or ProviderCapabilities(
            supports_native_tools=True,
            supports_json_schema=True,
            supports_beta_parse=False,
            supports_streaming=True,
        )
        self.base_url = base_url
        self.last_generate_mode = None
        self.last_decision_mode = None
        if client is not None:
            self.client = client
            return
        if OpenAI is None:
            raise ImportError("The openai package is required for OpenAI-compatible providers. Install project dependencies first.")
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def generate(
        self,
        *,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        model: str,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> Any:
        input_messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}, *messages]

        if response_schema is None:
            self.last_generate_mode = "text"
            return self._generate_text(model=model, messages=input_messages)

        if self.capabilities.supports_beta_parse:
            parsed = self._try_beta_parse(
                model=model,
                messages=input_messages,
                response_schema=response_schema,
            )
            if parsed is not None:
                self.last_generate_mode = "beta_parse"
                return parsed

        if self.capabilities.supports_json_schema:
            parsed = self._try_json_schema_response_format(
                model=model,
                messages=input_messages,
                response_schema=response_schema,
            )
            if parsed is not None:
                self.last_generate_mode = "json_schema"
                return parsed

        raw_text = self._generate_text(
            model=model,
            messages=[
                *input_messages,
                {
                    "role": "system",
                    "content": (
                        f"Return valid JSON only matching this schema exactly:\n"
                        f"{json.dumps(response_schema.model_json_schema(), ensure_ascii=False)}"
                    ),
                },
            ],
        )
        self.last_generate_mode = "text_json_fallback"
        return self._parse_model_from_text(raw_text, response_schema)

    def decide_action(
        self,
        *,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        model: str,
        tools: List[Dict[str, Any]],
        decision_schema: Type[BaseModel],
    ) -> BaseModel:
        input_messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}, *messages]

        if self.capabilities.supports_native_tools:
            native = self._try_native_tool_call(
                model=model,
                messages=input_messages,
                tools=tools,
                decision_schema=decision_schema,
            )
            if native is not None:
                self.last_decision_mode = "native_tools"
                return native

        if self.capabilities.supports_json_schema:
            parsed = self._try_json_schema_response_format(
                model=model,
                messages=[
                    *input_messages,
                    {
                        "role": "system",
                        "content": (
                            "Respond with a single JSON object only. "
                            "Use decision='tool' with tool + args when you want to act, "
                            "or decision='final' when done or blocked."
                        ),
                    },
                ],
                response_schema=decision_schema,
            )
            if parsed is not None:
                self.last_decision_mode = "json_schema"
                return parsed

        fallback_prompt = (
            "Return valid JSON only. Choose exactly one next step. "
            "If you need a tool, use this format: "
            '{"decision":"tool","tool":{"tool":"read_file","args":{"path":"..."},"reasoning":"..."}}. '
            "If complete or blocked, use this format: "
            '{"decision":"final","summary":"...","next_steps":[],"changed_files":[],"reasoning":"..."}.\n\n'
            f"Allowed tools schema:\n{json.dumps(tools, ensure_ascii=False)}\n\n"
            f"Decision schema:\n{json.dumps(decision_schema.model_json_schema(), ensure_ascii=False)}"
        )
        raw_text = self._generate_text(
            model=model,
            messages=[*input_messages, {"role": "system", "content": fallback_prompt}],
        )
        self.last_decision_mode = "text_json_fallback"
        return self._parse_model_from_text(raw_text, decision_schema)

    def _try_beta_parse(
        self,
        *,
        model: str,
        messages: List[Dict[str, Any]],
        response_schema: Type[BaseModel],
    ) -> Optional[BaseModel]:
        try:
            completion = self.client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=response_schema,
            )
            parsed = completion.choices[0].message.parsed
            if parsed is None:
                return None
            return parsed
        except Exception:
            return None

    def _try_json_schema_response_format(
        self,
        *,
        model: str,
        messages: List[Dict[str, Any]],
        response_schema: Type[BaseModel],
    ) -> Optional[BaseModel]:
        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": response_schema.__name__,
                        "schema": response_schema.model_json_schema(),
                    },
                },
            )
        except Exception:
            return None

        content = completion.choices[0].message.content
        if not content:
            return None
        try:
            return response_schema.model_validate_json(content)
        except ValidationError:
            return self._parse_model_from_text(content, response_schema)

    def _try_native_tool_call(
        self,
        *,
        model: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        decision_schema: Type[BaseModel],
    ) -> Optional[BaseModel]:
        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2,
                tools=tools,
                tool_choice="auto",
            )
        except Exception:
            return None

        message = completion.choices[0].message
        tool_calls = getattr(message, "tool_calls", None) or []
        if tool_calls:
            tool_call = tool_calls[0]
            raw_args = getattr(getattr(tool_call, "function", None), "arguments", "{}") or "{}"
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {"raw_arguments": raw_args}
            payload = {
                "decision": "tool",
                "tool": {
                    "tool": getattr(getattr(tool_call, "function", None), "name", "read_file"),
                    "args": args,
                    "reasoning": self._extract_text_content(message.content),
                },
            }
            try:
                return decision_schema.model_validate(payload)
            except ValidationError:
                return None

        content = self._extract_text_content(message.content)
        if not content:
            return None
        try:
            return self._parse_model_from_text(content, decision_schema)
        except ValidationError:
            return None

    def _generate_text(self, *, model: str, messages: List[Dict[str, Any]]) -> str:
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
        )
        message = completion.choices[0].message
        return self._extract_text_content(message.content)

    def _extract_text_content(self, content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text" and item.get("text"):
                        parts.append(str(item["text"]))
                    elif "content" in item:
                        parts.append(str(item["content"]))
                else:
                    text = getattr(item, "text", None)
                    if text:
                        parts.append(str(text))
            return "\n".join(part for part in parts if part).strip()
        return str(content)

    def _parse_model_from_text(self, raw_text: str, schema: Type[BaseModel]) -> BaseModel:
        text = raw_text.strip()
        if not text:
            raise ValidationError.from_exception_data(schema.__name__, [])

        candidates = [text]
        fenced = self._extract_json_code_block(text)
        if fenced:
            candidates.insert(0, fenced)
        json_slice = self._extract_json_object(text)
        if json_slice and json_slice not in candidates:
            candidates.insert(0, json_slice)

        last_error: Optional[Exception] = None
        for candidate in candidates:
            try:
                return schema.model_validate_json(candidate)
            except Exception as exc:  # noqa: BLE001
                last_error = exc

        if last_error is not None:
            raise last_error
        raise ValueError("Unable to parse model output")

    def _extract_json_code_block(self, text: str) -> Optional[str]:
        marker = "```"
        if marker not in text:
            return None
        start = text.find(marker)
        end = text.rfind(marker)
        if start == end:
            return None
        block = text[start + len(marker) : end].strip()
        if block.startswith("json"):
            block = block[4:].strip()
        return block or None

    def _extract_json_object(self, text: str) -> Optional[str]:
        start = text.find("{")
        if start == -1:
            return None
        depth = 0
        in_string = False
        escape = False
        for idx in range(start, len(text)):
            ch = text[idx]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : idx + 1]
        return None
