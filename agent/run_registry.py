from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class RunRecord:
    run_id: str
    created_at: str
    task: str
    provider: str
    model: str
    workspace: str
    artifact_dir: str
    step_count: int
    finished: bool
    summary: str
    changed_files: list[str]
    commands_run: list[str]
    next_steps: list[str]


class RunRegistry:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.base_dir / "registry.jsonl"
        self.sqlite_path = self.base_dir / "registry.sqlite3"
        self._init_sqlite()

    def _init_sqlite(self) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    task TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    workspace TEXT NOT NULL,
                    artifact_dir TEXT NOT NULL,
                    step_count INTEGER NOT NULL,
                    finished INTEGER NOT NULL,
                    summary TEXT NOT NULL,
                    changed_files_json TEXT NOT NULL,
                    commands_run_json TEXT NOT NULL,
                    next_steps_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def append(self, record: RunRecord) -> None:
        payload = asdict(record)
        with self.jsonl_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")

        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO runs (
                    run_id, created_at, task, provider, model, workspace, artifact_dir,
                    step_count, finished, summary, changed_files_json, commands_run_json, next_steps_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.run_id,
                    record.created_at,
                    record.task,
                    record.provider,
                    record.model,
                    record.workspace,
                    record.artifact_dir,
                    record.step_count,
                    1 if record.finished else 0,
                    record.summary,
                    json.dumps(record.changed_files, ensure_ascii=False),
                    json.dumps(record.commands_run, ensure_ascii=False),
                    json.dumps(record.next_steps, ensure_ascii=False),
                ),
            )
            conn.commit()

    def list_runs(self, limit: int = 20) -> list[RunRecord]:
        with sqlite3.connect(self.sqlite_path) as conn:
            rows = conn.execute(
                """
                SELECT run_id, created_at, task, provider, model, workspace, artifact_dir,
                       step_count, finished, summary, changed_files_json, commands_run_json, next_steps_json
                FROM runs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def get_run(self, run_id: str) -> RunRecord | None:
        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute(
                """
                SELECT run_id, created_at, task, provider, model, workspace, artifact_dir,
                       step_count, finished, summary, changed_files_json, commands_run_json, next_steps_json
                FROM runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def load_run_outputs(self, run_id: str) -> dict[str, Any]:
        record = self.get_run(run_id)
        if record is None:
            raise ValueError(f"Run not found: {run_id}")
        artifact_dir = Path(record.artifact_dir)
        outputs = artifact_dir / "outputs"
        prompts = artifact_dir / "prompts"
        data: dict[str, Any] = {
            "record": asdict(record),
            "events": self._read_jsonl(artifact_dir / "events.jsonl"),
            "task": self._read_text_if_exists(artifact_dir / "task.txt"),
            "final_summary": self._read_json_if_exists(outputs / "final_summary.json"),
            "run_state": self._read_json_if_exists(outputs / "run_state.json"),
            "plan": self._read_json_if_exists(outputs / "plan.json"),
            "available_prompt_files": sorted(str(p.name) for p in prompts.glob("*.json")),
            "available_output_files": sorted(str(p.name) for p in outputs.iterdir()) if outputs.exists() else [],
        }
        return data

    def _from_row(self, row: Any) -> RunRecord:
        return RunRecord(
            run_id=row[0],
            created_at=row[1],
            task=row[2],
            provider=row[3],
            model=row[4],
            workspace=row[5],
            artifact_dir=row[6],
            step_count=int(row[7]),
            finished=bool(row[8]),
            summary=row[9],
            changed_files=json.loads(row[10]),
            commands_run=json.loads(row[11]),
            next_steps=json.loads(row[12]),
        )

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _read_text_if_exists(self, path: Path) -> str | None:
        return path.read_text(encoding="utf-8") if path.exists() else None

    def _read_json_if_exists(self, path: Path) -> Any:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
