# dev-agent

A local-first development agent scaffold designed for code tasks such as:
- repo inspection
- planning
- file edits
- test execution
- review loops

## Current status

This is a v0/v1 scaffold that includes:
- provider abstraction for LM Studio / Ollama / OpenAI-compatible APIs
- core agent state and loop skeleton
- basic local tools
- CLI entrypoint
- room to extend with patching, retries, repo maps, and sandboxing

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Run:

```bash
dev-agent run \
  --task "Inspect this repo and propose a plan" \
  --provider lmstudio \
  --model qwen/qwen3-coder-30b \
  --workspace .
```

## Safety

The current shell tool is intentionally conservative:
- denylist for dangerous commands
- execution inside a chosen workspace
- timeout and output truncation

Before using this on real repositories, add:
- Docker sandboxing
- branch isolation
- patch-only writes
- approval gates for git commit/push
