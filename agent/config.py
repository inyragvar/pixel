from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    provider: str = Field(default=os.getenv("DEV_AGENT_PROVIDER", "lmstudio"))
    model: str = Field(default=os.getenv("DEV_AGENT_MODEL", "qwen/qwen3-coder-30b"))
    workspace: Path = Field(default=Path(os.getenv("DEV_AGENT_WORKSPACE", ".")).resolve())
    max_steps: int = Field(default=int(os.getenv("DEV_AGENT_MAX_STEPS", "8")))
    command_timeout: int = Field(default=int(os.getenv("DEV_AGENT_COMMAND_TIMEOUT", "60")))
    openai_api_key: str = Field(default=os.getenv("OPENAI_API_KEY", "dummy"))
    openai_base_url: str = Field(default=os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE") or "http://127.0.0.1:1234/v1")
    artifacts_dir_name: str = Field(default=os.getenv("DEV_AGENT_ARTIFACTS_DIR", ".dev-agent/runs"))
    edit_allowlist: str = Field(default=os.getenv("DEV_AGENT_EDIT_ALLOWLIST", "*"))
    edit_denylist: str = Field(default=os.getenv("DEV_AGENT_EDIT_DENYLIST", ""))
