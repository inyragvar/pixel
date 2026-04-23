from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any
from uuid import uuid4


class ArtifactStore:
    def __init__(self, root: Path, run_id: str | None = None) -> None:
        self.root = root
        self.run_id = run_id or root.name
        self.root.mkdir(parents=True, exist_ok=True)
        self.prompts_dir = self.root / "prompts"
        self.outputs_dir = self.root / "outputs"
        self.prompts_dir.mkdir(exist_ok=True)
        self.outputs_dir.mkdir(exist_ok=True)
        self.events_path = self.root / "events.jsonl"

    @classmethod
    def create(cls, base_dir: Path) -> "ArtifactStore":
        run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
        return cls(base_dir / run_id, run_id=run_id)

    def _json_default(self, value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if is_dataclass(value):
            return asdict(value)
        if isinstance(value, Path):
            return str(value)
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    def write_json(self, relative_path: str, payload: Any) -> Path:
        target = self.root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=self._json_default) + "\n", encoding="utf-8")
        return target

    def write_text(self, relative_path: str, content: str) -> Path:
        target = self.root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def append_event(self, event_type: str, payload: Any) -> None:
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "type": event_type,
            "payload": payload,
        }
        with self.events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=self._json_default) + "\n")
