from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ValidationError

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from agent.providers.base import Provider
from agent.providers.config import ProviderConfig


class OpenAICompatibleProvider(Provider):
    def __init__(self, *, config: ProviderConfig, client: Any | None = None) -> None:
        self.config = config
        self.provider_name = config.name
        self.capabilities = config.capabilities
        self.last_generate_mode = None
        self.last_decision_mode = None

        if client is not None:
            self.client = client
            return
        if OpenAI is None:
            raise ImportError(
                "The openai package is required for OpenAI-compatible providers. Install project dependencies first."
            )
        self.client = OpenAI(base_url=config.base_url, api_key=config.api_key)

    def generate(
        self,
        *,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        model: str,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> Any:
        input_messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}, *messages]
        self.last_generate_mode = None

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
                        "Return valid JSON only matching this schema exactly:\n"
                        f"{json.dumps(response_schema.model_json_schema(), ensure_ascii=False)}"
                    ),
                },
            ],
        )
        self.last_generate_mode = "json_text_fallback"
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
        self.last_decision_mode = None

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
                            "or decision='final' when done or blocked. "
                            "For tool args, always return a JSON object, never a JSON string."
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
            "Never return args as a string. Always return args as a JSON object.\n\n"
            f"Allowed tools schema:\n{json.dumps(tools, ensure_ascii=False)}\n\n"
            f"Decision schema:\n{json.dumps(decision_schema.model_json_schema(), ensure_ascii=False)}"
        )
        raw_text = self._generate_text(
            model=model,
            messages=[*input_messages, {"role": "system", "content": fallback_prompt}],
        )
        self.last_decision_mode = "json_text_fallback"
        parsed = self._parse_model_from_text(raw_text, decision_schema)
        return self._repair_decision(parsed, decision_schema)

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
            parsed = response_schema.model_validate_json(content)
        except ValidationError:
            parsed = self._parse_model_from_text(content, response_schema)
        return self._repair_decision(parsed, response_schema)

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
            args = self._normalize_tool_args(raw_args)
            payload = {
                "decision": "tool",
                "tool": {
                    "tool": getattr(getattr(tool_call, "function", None), "name", "read_file"),
                    "args": args,
                    "reasoning": self._extract_text_content(message.content),
                },
            }
            try:
                parsed = decision_schema.model_validate(payload)
            except ValidationError:
                return None
            return self._repair_decision(parsed, decision_schema)

        content = self._extract_text_content(message.content)
        if not content:
            return None
        try:
            parsed = self._parse_model_from_text(content, decision_schema)
        except ValidationError:
            return None
        return self._repair_decision(parsed, decision_schema)

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

    def _normalize_tool_args(self, raw_args: Any) -> Dict[str, Any]:
        if isinstance(raw_args, dict):
            return raw_args
        if isinstance(raw_args, str):
            raw_text = raw_args.strip()
            if not raw_text:
                return {}
            try:
                parsed = json.loads(raw_text)
                if isinstance(parsed, dict):
                    return parsed
                return {"value": parsed}
            except json.JSONDecodeError:
                json_slice = self._extract_json_object(raw_text)
                if json_slice:
                    try:
                        parsed = json.loads(json_slice)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        pass
                return {"raw_arguments": raw_text}
        return {"value": raw_args}

    def _repair_decision(self, parsed: BaseModel, schema: Type[BaseModel]) -> BaseModel:
        if not hasattr(parsed, "tool"):
            return parsed
        tool_action = getattr(parsed, "tool", None)
        if tool_action is None:
            return parsed

        args = getattr(tool_action, "args", None)
        normalized_args = self._normalize_tool_args(args)
        if normalized_args != args:
            payload = parsed.model_dump()
            payload["tool"]["args"] = normalized_args
            return schema.model_validate(payload)
        return parsed

    def _parse_model_from_text(self, raw_text: str, schema: Type[BaseModel]) -> BaseModel:
        text = raw_text.strip()
        if not text:
            raise ValidationError.from_exception_data(schema.__name__, [])

        candidates = [text]
        fenced = self._extract_json_code_block(text)
        if fenced:
            candidates.insert(0, fenced)
        json_slice = self._extract_json_object(text)
        if json_slice:
            candidates.insert(0, json_slice)

        seen: set[str] = set()
        errors: List[Exception] = []
        for candidate in candidates:
            candidate = candidate.strip()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            try:
                return schema.model_validate_json(candidate)
            except Exception as exc:
                errors.append(exc)
                try:
                    return schema.model_validate(json.loads(candidate))
                except Exception as exc2:
                    errors.append(exc2)

        raise errors[-1] if errors else ValidationError.from_exception_data(schema.__name__, [])

    def _extract_json_code_block(self, text: str) -> str | None:
        marker = "```json"
        start = text.find(marker)
        if start == -1:
            return None
        start += len(marker)
        end = text.find("```", start)
        if end == -1:
            return None
        return text[start:end].strip()

    def _extract_json_object(self, text: str) -> str | None:
        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
        return None
