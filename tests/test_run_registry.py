from __future__ import annotations

from pathlib import Path

from agent.artifacts import ArtifactStore
from agent.run_registry import RunRecord, RunRegistry


def test_registry_append_and_list(tmp_path: Path) -> None:
    registry = RunRegistry(tmp_path / '.dev-agent' / 'runs')
    artifact_store = ArtifactStore.create(tmp_path / '.dev-agent' / 'runs')
    record = RunRecord(
        run_id=artifact_store.run_id,
        created_at='2026-04-22T21:00:00Z',
        task='Inspect repo',
        provider='lmstudio',
        model='fake-model',
        workspace=str(tmp_path),
        artifact_dir=str(artifact_store.root),
        step_count=2,
        finished=True,
        summary='Done.',
        changed_files=['README.md'],
        commands_run=['pytest'],
        next_steps=['Review diff'],
    )
    registry.append(record)

    runs = registry.list_runs()
    assert len(runs) == 1
    assert runs[0].run_id == artifact_store.run_id
    assert registry.get_run(artifact_store.run_id) is not None


def test_registry_load_run_outputs(tmp_path: Path) -> None:
    registry = RunRegistry(tmp_path / '.dev-agent' / 'runs')
    artifact_store = ArtifactStore.create(tmp_path / '.dev-agent' / 'runs')
    artifact_store.write_text('task.txt', 'Inspect repo\n')
    artifact_store.write_json('outputs/final_summary.json', {'summary': 'Done.', 'changed_files': []})
    artifact_store.write_json('outputs/plan.json', {'summary': 'Plan', 'steps': []})
    artifact_store.append_event('run_started', {'task': 'Inspect repo'})

    registry.append(
        RunRecord(
            run_id=artifact_store.run_id,
            created_at='2026-04-22T21:00:00Z',
            task='Inspect repo',
            provider='lmstudio',
            model='fake-model',
            workspace=str(tmp_path),
            artifact_dir=str(artifact_store.root),
            step_count=1,
            finished=True,
            summary='Done.',
            changed_files=[],
            commands_run=[],
            next_steps=[],
        )
    )

    payload = registry.load_run_outputs(artifact_store.run_id)
    assert payload['record']['run_id'] == artifact_store.run_id
    assert payload['task'] == 'Inspect repo\n'
    assert payload['final_summary']['summary'] == 'Done.'
    assert payload['events'][0]['type'] == 'run_started'
