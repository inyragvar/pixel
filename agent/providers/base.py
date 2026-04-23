from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import field
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel


class Provider(ABC):
    provider_name: str = "unknown"
    capabilities: Any = None
    last_generate_mode: str | None = None
    last_decision_mode: str | None = None

    @abstractmethod
    def generate(
        self,
        *,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        model: str,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def decide_action(
        self,
        *,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        model: str,
        tools: List[Dict[str, Any]],
        decision_schema: Type[BaseModel],
    ) -> BaseModel:
        raise NotImplementedError
