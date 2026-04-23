from __future__ import annotations

import os
from pathlib import Path
from typing import List


from pydantic import BaseModel, Field


def _parse_csv_env(value: str | None) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_bool_env(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    provider: str = Field(default=os.getenv("DEV_AGENT_PROVIDER", "lmstudio"))
    model: str = Field(default=os.getenv("DEV_AGENT_MODEL", "qwen/qwen3-coder-30b"))
    workspace: Path = Field(default=Path(os.getenv("DEV_AGENT_WORKSPACE", ".")).resolve())
    max_steps: int = Field(default=int(os.getenv("DEV_AGENT_MAX_STEPS", "8")))
    command_timeout: int = Field(default=int(os.getenv("DEV_AGENT_COMMAND_TIMEOUT", "60")))
    openai_api_key: str = Field(default=os.getenv("OPENAI_API_KEY", "dummy"))
    openai_base_url: str = Field(
        default=(
            os.getenv("OPENAI_BASE_URL")
            or os.getenv("OPENAI_API_BASE")
            or "http://127.0.0.1:1234/v1"
        )
    )
    edit_allowlist: List[str] = Field(default_factory=lambda: _parse_csv_env(os.getenv("DEV_AGENT_EDIT_ALLOWLIST")))
    edit_denylist: List[str] = Field(default_factory=lambda: _parse_csv_env(os.getenv("DEV_AGENT_EDIT_DENYLIST")))

    isolate_workspace: bool = Field(default=_parse_bool_env(os.getenv("DEV_AGENT_ISOLATE_WORKSPACE"), True))
    keep_isolated_workspace: bool = Field(default=_parse_bool_env(os.getenv("DEV_AGENT_KEEP_ISOLATED_WORKSPACE"), False))
