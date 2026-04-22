# TODO.md

# AI Development Agent TODO

## Status Legend

- [ ] not started
- [~] in progress
- [x] done
- [!] blocked / needs decision

---

## 1. Project Setup

- [ ] Create repository
- [ ] Choose project name
- [ ] Initialize Python project with `pyproject.toml`
- [ ] Set Python version target (recommended: 3.12+)
- [ ] Create virtual environment setup instructions
- [ ] Add formatter/linter configuration
- [ ] Add test runner configuration
- [ ] Create base directory structure
- [ ] Add `.env.example`
- [ ] Add `.gitignore`
- [ ] Add `README.md`
- [ ] Add `PLAN.md`
- [ ] Add `TODO.md`

### Decisions

- [ ] Pick packaging tool (`uv`, `poetry`, or `pip + venv`)
- [ ] Pick CLI framework (`typer` preferred, or `click`)
- [ ] Pick logging format (plain text + JSONL recommended)

---

## 2. Core Dependencies

- [ ] Add OpenAI SDK dependency
- [ ] Add HTTP client dependency (`httpx`)
- [ ] Add schema validation dependency (`pydantic`)
- [ ] Add CLI dependency
- [ ] Add testing dependencies (`pytest`, `pytest-asyncio` if needed)
- [ ] Add diff/patch helper dependency if needed
- [ ] Add dotenv/config dependency if needed

### Optional early dependencies

- [ ] Add rich console output (`rich`)
- [ ] Add retry helper (`tenacity`)
- [ ] Add SQLite helper if needed

---

## 3. Configuration Layer

- [ ] Create config model
- [ ] Support environment-based configuration
- [ ] Add provider selection config
- [ ] Add model selection config
- [ ] Add LM Studio endpoint config
- [ ] Add Ollama endpoint config
- [ ] Add OpenAI API config
- [ ] Add command timeout config
- [ ] Add token/output budget config
- [ ] Add workspace path config
- [ ] Add approval mode config

### Example settings

- [ ] `DEFAULT_PROVIDER`
- [ ] `DEFAULT_MODEL`
- [ ] `LMSTUDIO_BASE_URL`
- [ ] `OLLAMA_BASE_URL`
- [ ] `OPENAI_API_KEY`
- [ ] `MAX_TOOL_CALLS`
- [ ] `MAX_REPAIR_LOOPS`
- [ ] `COMMAND_TIMEOUT_SECONDS`

---

## 4. Provider Abstraction

### Base provider

- [ ] Create `LLMProvider` base interface
- [ ] Define common request/response schema
- [ ] Define structured output interface
- [ ] Define tool-calling interface
- [ ] Define streaming interface
- [ ] Define capability flags

### LM Studio provider

- [ ] Implement LM Studio adapter
- [ ] Support OpenAI-compatible chat/responses flow
- [ ] Support structured output mode where possible
- [ ] Normalize tool call output
- [ ] Add connectivity test command

### Ollama provider

- [ ] Implement Ollama adapter
- [ ] Support OpenAI-compatible flow
- [ ] Normalize tool call output
- [ ] Add structured output support if model supports it
- [ ] Add connectivity test command

### OpenAI provider

- [ ] Implement OpenAI adapter
- [ ] Support Responses-style flow
- [ ] Normalize tool call output
- [ ] Add connectivity test command

### Provider tests

- [ ] Unit test request normalization
- [ ] Unit test tool-call normalization
- [ ] Unit test structured output parsing
- [ ] Unit test failure handling

---

## 5. CLI Interface

- [ ] Create CLI entrypoint
- [ ] Add `run-task` command
- [ ] Add `provider-test` command
- [ ] Add `models` command if useful
- [ ] Add `summarize-repo` command
- [ ] Add `show-config` command
- [ ] Add verbose/debug flags
- [ ] Add dry-run mode

### Nice-to-have

- [ ] Add interactive task prompt mode
- [ ] Add colored output
- [ ] Add run summary table

---

## 6. State and Run Model

- [ ] Define run state schema
- [ ] Define task schema
- [ ] Define plan schema
- [ ] Define tool action schema
- [ ] Define result schema
- [ ] Define error schema
- [ ] Define repair loop counters
- [ ] Define budget tracking fields
- [ ] Define files-read/files-changed tracking

---

## 7. Tool Layer - Filesystem

- [ ] Implement `list_files`
- [ ] Implement `read_file`
- [ ] Implement `read_files`
- [ ] Implement file size limit protection
- [ ] Implement path normalization
- [ ] Implement repo-root enforcement
- [ ] Implement `write_file`
- [ ] Implement `apply_patch`
- [ ] Prevent writes outside repo root

### Filesystem tests

- [ ] Test read existing file
- [ ] Test reject missing file
- [ ] Test reject path traversal
- [ ] Test write inside repo root
- [ ] Test reject write outside repo root
- [ ] Test patch application success
- [ ] Test patch failure handling

---

## 8. Tool Layer - Search

- [ ] Implement `search_code`
- [ ] Use `rg` / ripgrep if available
- [ ] Add fallback pure-Python search if needed
- [ ] Add filename filtering
- [ ] Add extension filtering
- [ ] Add max results limit
- [ ] Add context lines support

### Later

- [ ] Add symbol search
- [ ] Add semantic search
- [ ] Add embeddings-backed search

---

## 9. Tool Layer - Shell and Validation

- [ ] Implement `run_command`
- [ ] Add working directory enforcement
- [ ] Add timeout support
- [ ] Add stdout/stderr capture
- [ ] Add output truncation
- [ ] Add exit code handling
- [ ] Add command allowlist or safety policy

### Validation wrappers

- [ ] Implement `run_tests`
- [ ] Implement `run_linter`
- [ ] Implement `run_typecheck`
- [ ] Implement `run_build`

### Tests

- [ ] Test successful command
- [ ] Test timeout behavior
- [ ] Test output truncation
- [ ] Test blocked command
- [ ] Test working directory enforcement

---

## 10. Tool Layer - Git

- [ ] Implement `git_status`
- [ ] Implement `git_diff`
- [ ] Implement `git_current_branch`
- [ ] Implement optional `create_branch`
- [ ] Implement optional `commit_changes`
- [ ] Block commit unless explicitly approved
- [ ] Never auto-push by default

### Tests

- [ ] Test git status read
- [ ] Test git diff read
- [ ] Test commit blocked without approval

---

## 11. Prompt and Schema Design

- [ ] Create planner prompt
- [ ] Create executor prompt
- [ ] Create reviewer prompt
- [ ] Create repair prompt
- [ ] Define plan schema
- [ ] Define action schema
- [ ] Define final summary schema
- [ ] Define failure explanation schema

### Prompt rules

- [ ] Keep tool instructions explicit
- [ ] Tell model not to invent files/commands
- [ ] Require bounded file selection
- [ ] Require concise step reasoning output where useful
- [ ] Require final summary with changed files and validation result

---

## 12. Agent Loop

### Basic flow

- [ ] Implement task intake
- [ ] Implement repo inspection step
- [ ] Implement planning step
- [ ] Implement context gathering step
- [ ] Implement execution step
- [ ] Implement validation step
- [ ] Implement repair loop
- [ ] Implement finish step

### Budget control

- [ ] Add max step limit
- [ ] Add max tool-call limit
- [ ] Add max repair loop limit
- [ ] Add max changed files limit
- [ ] Add max command count limit

### Failure handling

- [ ] Stop on repeated malformed actions
- [ ] Stop on repeated blocked commands
- [ ] Stop when repo becomes unsafe to continue
- [ ] Return useful error summary on failure

---

## 13. Logging and Persistence

- [ ] Create run log structure
- [ ] Write logs to JSONL or SQLite
- [ ] Store task input
- [ ] Store provider/model used
- [ ] Store tool calls
- [ ] Store file reads/writes
- [ ] Store command outputs
- [ ] Store final diff summary
- [ ] Store validation result
- [ ] Store timings

### Nice-to-have

- [ ] Add replay/debug command
- [ ] Add run history command
- [ ] Add pretty HTML/Markdown run export

---

## 14. Repo Intelligence

### First pass

- [ ] Generate repo tree summary
- [ ] Detect common project files (`pyproject.toml`, `package.json`, etc.)
- [ ] Detect common commands from repo files
- [ ] Create module summaries
- [ ] Cache repo summary per run or workspace

### Later

- [ ] Build symbol index
- [ ] Build import graph
- [ ] Map tests to implementation files
- [ ] Add semantic search index
- [ ] Add embeddings cache

---

## 15. Safety and Approval System

- [ ] Define safe action list
- [ ] Define medium-risk action list
- [ ] Define high-risk action list
- [ ] Add approval gate for commits
- [ ] Add approval gate for deletes
- [ ] Add approval gate for destructive commands
- [ ] Add approval gate for wide-scope rewrites
- [ ] Add dry-run option for risky actions where possible

---

## 16. Testing Strategy

### Unit tests

- [ ] Providers
- [ ] Config
- [ ] State schemas
- [ ] Filesystem tools
- [ ] Search tools
- [ ] Shell tools
- [ ] Git tools
- [ ] Agent loop transitions

### Integration tests

- [ ] Simple Python repo task
- [ ] Simple Node repo task
- [ ] Failing test repair task
- [ ] Documentation update task
- [ ] Patch failure recovery task

### Scenario tests

- [ ] “Fix failing test” scenario
- [ ] “Implement missing function” scenario
- [ ] “Refactor bounded module” scenario
- [ ] “Update docs after change” scenario

---

## 17. v1 Acceptance Checklist

- [ ] Can connect to LM Studio
- [ ] Can connect to Ollama
- [ ] Can connect to OpenAI
- [ ] Can inspect repo safely
- [ ] Can read and search files
- [ ] Can propose a structured plan
- [ ] Can apply code changes
- [ ] Can run validation commands
- [ ] Can retry on failure
- [ ] Can produce final diff summary
- [ ] Does not commit or push without approval
- [ ] Stores usable logs for debugging

---

## 18. Phase 2 TODOs

- [ ] Add structured output everywhere
- [ ] Add better provider capability detection
- [ ] Add repo summary cache
- [ ] Add better patch application strategy
- [ ] Add reviewer stage
- [ ] Add improved repair prompts
- [ ] Add budget analytics
- [ ] Add SQLite run store
- [ ] Add branch-per-task support

---

## 19. Phase 3 TODOs

- [ ] Add semantic search
- [ ] Add symbol-aware file selection
- [ ] Add embeddings index
- [ ] Add architecture summary memory
- [ ] Add test-to-code mapping
- [ ] Add module ownership hints
- [ ] Add cross-file refactor support

---

## 20. Phase 4 TODOs

- [ ] Split planner/executor/reviewer prompts cleanly
- [ ] Add internal review pass before finish
- [ ] Add specialized test-fix loop
- [ ] Add documentation sync pass
- [ ] Add optional multi-agent orchestration mode

---

## 21. Phase 5 TODOs

- [ ] Add GitHub integration
- [ ] Add GitLab integration
- [ ] Add PR creation support
- [ ] Add PR review mode
- [ ] Add issue tracker integration
- [ ] Add CI result ingestion
- [ ] Add web dashboard
- [ ] Add VS Code integration

---

## 22. Immediate Next Actions

These are the best first actions right now.

- [ ] Create repo skeleton
- [ ] Implement config layer
- [ ] Implement provider interface
- [ ] Implement LM Studio provider first
- [ ] Implement CLI `run-task`
- [ ] Implement read/search tools
- [ ] Implement shell/test runner
- [ ] Implement minimal state-driven loop
- [ ] Run first end-to-end task on a small repo

---

## 23. Nice-to-Have Later

- [ ] TUI interface
- [ ] Live token/cost tracking
- [ ] Model routing by task type
- [ ] Parallel retrieval workers
- [ ] Cached file chunk summaries
- [ ] Background indexing daemon
- [ ] Dockerized executor service
- [ ] Remote worker execution

---

## 24. First Milestone Definition

The first milestone is complete when:

- the agent can take a coding task
- inspect a real repo
- select relevant files
- edit code safely
- run validation
- retry at least once after failure
- show final diff and summary
- avoid dangerous git actions by default
