from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class Provider(ABC):
    @abstractmethod
    def generate(
        self,
        *,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        model: str,
        response_schema: Optional[type] = None,
    ) -> Any:
        raise NotImplementedError
