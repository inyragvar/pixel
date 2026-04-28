# dev-agent

`dev-agent` is a local-first development agent scaffold for repository inspection, planning, tool-driven execution, file edits, validation, and iterative repair.

It is designed to work with:
- **LM Studio** on a local or remote machine
- **Ollama**
- **OpenAI-compatible** endpoints

The current scaffold already includes a **real bounded action loop**. The model can choose the next tool, execute it, observe the result, and continue until it returns a final answer or the loop reaches its step limit.

---

## Current status

This project is an early **v1 scaffold**.

Implemented now:
- provider abstraction for LM Studio / Ollama / OpenAI-compatible APIs
- bounded agent loop with action/observation history
- planner + reviewer scaffolding
- provider-level action generation with fallbacks:
  - native tool calling
  - JSON-schema response format
  - plain JSON text fallback
- local tools for:
  - file listing and file reading
  - file writing and appending
  - targeted in-file replacement
  - unified-diff `apply_patch` edits
  - code search via `rg`
  - safer shell command execution with dangerous command blocking
  - git status and diff
- CLI entrypoint
- per-run artifact storage under `.dev-agent/runs/<run-id>/`
- persisted run registry in both JSONL and SQLite
- replay/list support for past runs
- project detection + validation profiles for Python / Node / Go / Rust
- `run_validation` tool for automatic sensible validation commands
- test coverage for loop flow, filesystem, repo map, provider parsing, run registry, and project detection

Not implemented yet:
- Docker sandbox / isolated task workspace
- approval gates for dangerous actions
- resumable runs
- semantic code index / embeddings
- GitHub / PR / issue tracker integrations

---

## Architecture overview

```text
CLI
  -> Settings / Config
  -> Provider factory
  -> Agent loop
       -> Planner
       -> Executor
            -> filesystem tool
            -> search tool
            -> shell tool
            -> git tool
       -> Reviewer
  -> Final summary / changed files / commands run
```

### Provider layer
The provider layer hides differences between backends.

Current behavior:
1. try native tool calling if supported by the backend/model
2. fall back to JSON schema response formatting if available
3. fall back again to plain JSON text parsing

This makes the scaffold much more tolerant of local models that are inconsistent about strict schema following.

### Agent loop
The loop currently works like this:
1. create an initial plan
2. build a transcript from notes + prior observations
3. ask the model for the single best next decision
4. either:
   - execute a tool, record the result, and continue
   - or finalize with a summary
5. if no clean final answer is produced before the step budget is exhausted, ask the reviewer for a closing summary

### Executor
The executor exposes:
- available tool names
- JSON tool schemas
- tool dispatch
- tracking of changed files and commands run

---

## Project layout

```text
dev-agent/
├── agent/
│   ├── config.py
│   ├── core/
│   │   ├── executor.py
│   │   ├── loop.py
│   │   ├── planner.py
│   │   ├── prompts.py
│   │   ├── reviewer.py
│   │   └── state.py
│   ├── memory/
│   │   └── repo_map.py
│   ├── providers/
│   │   ├── base.py
│   │   ├── factory.py
│   │   └── openai_compatible.py
│   ├── schemas/
│   │   ├── actions.py
│   │   ├── outputs.py
│   │   └── plan.py
│   └── tools/
│       ├── filesystem.py
│       ├── git_tools.py
│       ├── search.py
│       └── shell.py
├── cli.py
├── tests/
├── README.md
└── pyproject.toml
```

---

## Requirements

Recommended baseline:
- **Python 3.12**

Current metadata is compatible with newer Python too, and the scaffold was validated in this environment on Python 3.13, but Python 3.12 is the intended baseline.

External tools:
- `git`
- `rg` / `ripgrep`
- a reachable model backend such as LM Studio or Ollama

---

## Quick start

### 1. Create environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m pip install -U pytest
```

### 2. Configure environment

Create a local `.env` or export environment variables directly.

Typical variables:

```env
DEV_AGENT_PROVIDER=lmstudio
DEV_AGENT_MODEL=qwen/qwen3-coder-30b
DEV_AGENT_WORKSPACE=.
DEV_AGENT_MAX_STEPS=8
DEV_AGENT_COMMAND_TIMEOUT=60
OPENAI_API_KEY=dummy
OPENAI_BASE_URL=http://127.0.0.1:1234/v1
```

Examples:
- LM Studio remote host:
  - `OPENAI_BASE_URL=http://192.168.1.238:1234/v1`
- Ollama:
  - point `OPENAI_BASE_URL` to your Ollama OpenAI-compatible endpoint if you expose one

### 3. Run the agent

```bash
export OPENAI_BASE_URL=http://192.168.1.238:1234/v1
export OPENAI_API_KEY=dummy
export OLLAMA_BASE_URL=http://192.168.1.238:11434

dev-agent \
  --task "Inspect this repo and propose the best next change" \
  --provider lmstudio \
  --model qwen/qwen3-coder-30b \
  --workspace .
```

---

## What the CLI currently returns

The current CLI flow returns:
- plan summary
- final summary
- changed files
- commands run
- recent agent history
- run ID
- artifact directory
- optional machine-readable JSON via `--json`

This is enough to support early debugging and iteration on the agent loop.


### Safe isolated run

Run tools against a temporary copy instead of the live repository:

```bash
dev-agent \
  --task "Inspect this repo, make one safe improvement, and run validation" \
  --workspace . \
  --isolated-workspace \
  --keep-isolated
```

Use this mode when testing weaker local models or when you want to inspect changes before copying them back manually.

### Machine-readable run output

```bash
dev-agent \
  --task "Detect this project and run validation" \
  --workspace . \
  --json
```

The JSON output includes the run ID, artifact directory, plan, final summary, changed files, commands run, and workspace mode.

### Run artifacts

Every normal run is saved under `.dev-agent/runs/<run-id>/` and includes:

```text
task.txt
events.jsonl
prompts/
outputs/plan.json
outputs/step_XX_tool.json
outputs/step_XX_result.txt
outputs/final_summary.json
outputs/run_state.json
outputs/final_git_status.txt
outputs/final_git_diff.patch
```

### Run history commands

List past runs:

```bash
dev-agent --list-runs --workspace .
```

Replay a stored run:

```bash
dev-agent --replay-run <run-id> --workspace .
```

Stored metadata lives in:
- JSONL: `.dev-agent/runs/registry.jsonl`
- SQLite: `.dev-agent/runs/registry.sqlite3`

---

## Current tools

### FileSystemTool
- `list_files(path=".")`
- `read_file(path)`
- `write_file(path, content)`
- `append_file(path, content)`
- `replace_in_file(path, old, new, count=1)`

### SearchTool
- `search_code(query)`

Requires `rg`.

### ValidationTool
- `detect_project()`
- `run_validation(mode="all")`

Supported profiles:
- Python: pytest / ruff / mypy / compileall when applicable
- Node: package.json scripts via npm / pnpm / yarn
- Go: `go test ./...`, `go vet ./...`, `go build ./...`
- Rust: `cargo test`, `cargo check`, `cargo build`, `cargo clippy ...`

### ShellTool
- `run_command(command)`

Current safeguards:
- workspace-local execution
- timeout
- output truncation
- small denylist for obviously dangerous commands

### GitTool
- `status()`
- `diff()`

---

## Safety notes

This scaffold is **not yet hardened**.

Current protections are only basic.
Before using this on important repositories, add at least:
- isolated per-task worktree or temp clone
- Docker sandboxing
- command allowlist or stronger policy layer
- approval gates for write / git / destructive actions
- branch isolation
- patch-only edits for most cases
- secrets redaction in logs

Do not grant this unrestricted execution on sensitive machines in its current form.

---

## Testing

Run:

```bash
python -m pytest -v
python -m pytest tests/test_loop.py -v
python -m pytest -k action
```

Current tests cover:
- bounded loop flow
- filesystem behavior
- repo map behavior
- provider parsing fallbacks

---

## Recommended next implementation steps

1. add provider-specific adapters and capability flags
2. add unified diff / patch application
3. introduce isolated task workspaces
4. improve shell safety and approval gates
5. add repo map + symbol-aware retrieval to the main loop
6. add streaming and persisted run logs
7. add GitHub / PR integrations

More detailed execution tracking lives in `TODO.md`.


## Run artifacts

Each run now writes structured artifacts under `.dev-agent/runs/<run-id>/` inside the workspace.

Artifacts include:
- `task.txt`
- `events.jsonl`
- `prompts/plan_prompt.json`
- `prompts/step_XX_decision_prompt.json`
- `outputs/plan.json`
- `outputs/step_XX_tool.json`
- `outputs/step_XX_result.txt`
- `outputs/final_summary.json`
- `outputs/run_state.json`

Set `DEV_AGENT_ARTIFACTS_DIR` to change the artifact root relative to the workspace.
