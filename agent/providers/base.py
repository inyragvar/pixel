from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel

from agent.providers.capabilities import ProviderCapabilities


class Provider(ABC):
    capabilities: ProviderCapabilities
    provider_name: str
    last_generate_mode: Optional[str] = None
    last_decision_mode: Optional[str] = None

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
