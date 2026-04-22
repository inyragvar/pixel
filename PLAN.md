# PLAN.md

# AI Development Agent Plan

## 1. Goal

Build a practical AI development agent that can:

- work against local and remote LLM backends
- use LM Studio on another machine for large-context reasoning
- support OpenAI-compatible integrations
- support Ollama-based integrations
- inspect repositories
- read and modify code safely
- run tests and validation commands
- produce clear diffs, summaries, and approval checkpoints

The first version should be intentionally narrow, reliable, and useful.

It should **not** start as a fully autonomous software engineer.
It should start as a controlled coding agent with strong tooling and safe execution boundaries.

---

## 2. Core Product Direction

### Primary objective

Create a developer-focused agent that can take a task such as:

- fix failing tests
- implement a feature in a bounded module
- refactor selected files
- add documentation
- investigate build errors

and then:

1. inspect the codebase
2. build a task plan
3. choose relevant files
4. edit code
5. run validation commands
6. repair failures
7. show results before any destructive or remote action

### Non-goals for v1

The first version should **not** include:

- automatic push to remote repositories by default
- unrestricted shell execution
- complex multi-agent orchestration
- full IDE extension work
- broad internet browsing by default
- fully autonomous long-running background jobs
- complete repo ingestion into prompt context every turn

---

## 3. Language Decision

## Recommended language: Python

Python is the best fit for the first implementation because it gives the best balance of:

- speed of development
- mature SDK support
- easy tool execution
- strong support for structured outputs
- good ecosystem for code parsing, search, embeddings, testing, and evaluation
- flexible orchestration for agent workflows

### Why Python is the right first choice

- excellent support for OpenAI-compatible APIs
- straightforward integration with LM Studio and Ollama
- easy subprocess and filesystem control
- strong libraries for CLI, schemas, persistence, testing, and async execution
- best environment for rapid experimentation before architecture stabilizes

### Secondary language later: TypeScript

TypeScript should be added later if needed for:

- web UI
- dashboard
- VS Code integration
- browser-based controls
- collaboration features

### Lower-priority languages

- **Go**: good for infra services and lightweight daemons, but slower for agent experimentation
- **Rust**: good for hardened execution and sandboxing, but not the best first language for fast agent iteration

### Final decision

Use:

- **Python** for core agent runtime
- **TypeScript** later for UI or editor integrations
- optionally **Rust/Go** later for isolated runner or hardened execution services

---

## 4. High-Level Architecture

The system should be divided into clear layers.

## 4.1 Provider Layer

This layer abstracts model access.

It should support:

- LM Studio provider
- Ollama provider
- OpenAI provider

All providers should implement a common interface so that the agent logic does not depend on one vendor.

### Responsibilities

- send prompts/messages
- support tool-calling flows when available
- support structured output mode
- support streaming where needed
- normalize model responses
- normalize tool-call format
- expose capability flags

### Key design rule

The agent should depend on an internal `LLMProvider` interface, not directly on any one SDK.

---

## 4.2 Agent Core

The core agent should manage task execution through explicit stages.

### Initial execution stages

1. task intake
2. repository inspection
3. planning
4. context gathering
5. execution
6. validation
7. repair loop
8. result packaging
9. approval checkpoint

### Core responsibilities

- track task state
- control loop progress
- call model provider
- invoke tools
- log all actions
- stop when success, failure, or budget limit is reached

### Design rule

Use a **state-driven loop**, not a giant chat loop with implicit behavior.

---

## 4.3 Tool Layer

The tool layer should expose narrow, deterministic functions.

### Required v1 tools

- `list_files`
- `read_file`
- `read_files`
- `search_code`
- `write_file`
- `apply_patch`
- `run_command`
- `run_tests`
- `git_status`
- `git_diff`

### Later tools

- `semantic_search`
- `symbol_lookup`
- `run_linter`
- `run_typecheck`
- `create_branch`
- `commit_changes`
- `open_pr`
- `browser_fetch`
- `issue_tracker_lookup`

### Design rule

Prefer many small tools over one vague “do everything” tool.

---

## 4.4 Memory and Context Layer

The agent should use structured context buckets.

### Context buckets

#### Task context

- user goal
- acceptance criteria
- constraints
- task status

#### Working context

- files already read
- discovered errors
- generated plan
- pending actions
- recent tool outputs

#### Project memory

- codebase summaries
- module summaries
- conventions
- known commands
- architectural notes

### Important principle

Even with large context windows, do not pass the whole repo every turn.
Use:

- repo map
- summaries
- selected files
- targeted search

Large context should improve reasoning, not replace retrieval discipline.

---

## 4.5 Execution Layer

The execution layer runs commands and applies edits.

### v1 execution model

- local subprocess execution
- repository path allowlist
- command timeout
- output truncation
- explicit approval for risky actions

### Later execution model

- per-task workspace copy
- Docker sandbox
- resource limits
- network restrictions
- destructive command approval levels

---

## 5. Product Phases

## Phase 1: Minimal Useful Agent

### Objective

Build a safe CLI development agent that can complete bounded repository tasks.

### Scope

- accept a task from CLI
- inspect repository structure
- search and read files
- generate a plan
- edit files
- run tests/build/lint
- retry a limited number of times
- produce summary and diff

### Success criteria

- can complete simple implementation tasks in a local repo
- can fix a subset of failing tests
- can modify files without corrupting project structure
- can show clear final output and validation results

---

## Phase 2: Reliability and Safety

### Objective

Make the agent stable enough for repeated use on real projects.

### Additions

- structured outputs for planning and tool calls
- command allowlist or policy engine
- retry strategy
- explicit action budgets
- persistent session logs
- approval gates
- rollback to clean state when possible

### Success criteria

- fewer malformed tool calls
- reproducible runs
- bounded behavior under failure
- clear audit trail per task

---

## Phase 3: Codebase Intelligence

### Objective

Improve repo understanding and reduce wasted context.

### Additions

- repo map generation
- symbol index
- module summaries
- semantic search
- optional embeddings index
- test-to-code mapping

### Success criteria

- faster task startup
- better file selection
- better architectural reasoning
- fewer unnecessary reads of unrelated files

---

## Phase 4: Multi-Role Internal Workflow

### Objective

Separate planning, execution, and review logic for better quality.

### Additions

- planner role
- executor role
- reviewer role
- test-fix repair role

These may still run inside one process with separate prompts and schemas.

### Success criteria

- better task decomposition
- fewer careless edits
- improved repair loop quality

---

## Phase 5: Extended Integrations

### Objective

Make the agent useful in a broader engineering workflow.

### Additions

- GitHub/GitLab integration
- issue tracker integration
- PR generation
- PR review mode
- CI result ingestion
- dashboard/UI
- VS Code integration

---

## 6. Provider Strategy

## 6.1 LM Studio

LM Studio should be used as the primary high-context backend running on another machine.

### Best use cases

- repo understanding
- large planning tasks
- architecture changes
- summarization of many files
- cross-module analysis

### Notes

- keep remote endpoint configurable
- treat model capability differences as runtime metadata
- avoid assuming perfect tool-calling behavior from every model

---

## 6.2 Ollama

Ollama should serve as a secondary or alternative backend.

### Best use cases

- local execution fallback
- smaller/faster models for repair loops
- structured-output tasks where supported
- experimentation with different coding models

---

## 6.3 OpenAI

OpenAI should be optional but supported through the same internal provider abstraction.

### Best use cases

- stronger cloud reasoning when needed
- fallback for difficult tasks
- comparison and evaluation

---

## 7. Context Strategy

The system should use a layered context strategy rather than relying entirely on raw context size.

### Recommended approach

#### Small tasks

- task description
- repo map
- selected files
- recent outputs

#### Medium tasks

- add module summaries
- add error logs
- add related tests

#### Large tasks

- use high-context model
- feed architecture summary first
- then selected files
- then staged tool-based retrieval

### Rule

Use big context for **important reasoning**, not as a substitute for indexing and search.

---

## 8. Safety Model

The agent must behave as a controlled engineering tool.

### Approval categories

#### Safe actions

- read files
- search files
- run non-destructive tests
- list diffs

#### Medium-risk actions

- write files
- patch code
- run formatting
- run migrations in dry-run mode

#### High-risk actions

- delete files
- run destructive shell commands
- rewrite large project areas
- commit changes
- push branches

### Rule

High-risk actions require explicit approval.

---

## 9. Observability and Logging

The system should store detailed run data.

### Per run store

- task input
- selected model/provider
- prompts sent
- tool calls made
- files touched
- command outputs
- diffs generated
- validation outcomes
- timing
- token usage when available

### Why this matters

- debugging
- evaluation
- reproducibility
- performance tuning
- provider comparison

---

## 10. Testing Strategy

The project should include tests from the start.

### Test layers

#### Unit tests

- provider adapters
- tool functions
- state transitions
- parsing and schema validation

#### Integration tests

- repository task flows
- file edit flows
- command execution
- repair loops

#### Scenario tests

- fix failing unit test
- implement missing function
- update docs after code change
- recover from malformed model output

---

## 11. Suggested Project Structure

```text
my-agent/
├── agent/
│   ├── providers/
│   │   ├── base.py
│   │   ├── lmstudio_provider.py
│   │   ├── ollama_provider.py
│   │   └── openai_provider.py
│   ├── core/
│   │   ├── state.py
│   │   ├── loop.py
│   │   ├── planner.py
│   │   ├── executor.py
│   │   └── reviewer.py
│   ├── tools/
│   │   ├── filesystem.py
│   │   ├── search.py
│   │   ├── shell.py
│   │   ├── git_tools.py
│   │   └── tests.py
│   ├── memory/
│   │   ├── repo_map.py
│   │   ├── summaries.py
│   │   └── session_store.py
│   ├── schemas/
│   │   ├── plan.py
│   │   ├── actions.py
│   │   └── result.py
│   ├── config.py
│   └── app.py
├── prompts/
├── tests/
├── scripts/
├── cli.py
└── pyproject.toml
```

---

## 12. Recommended Development Sequence

1. build provider abstraction
2. build CLI entrypoint
3. build read/search tools
4. build patch/write tools
5. build shell/test execution
6. build state-driven agent loop
7. add structured outputs
8. add logging and persistence
9. add repo map and summaries
10. add approval gates
11. add reviewer/repair improvements
12. add UI/editor integrations later

---

## 13. Definition of v1 Done

Version 1 is done when the agent can:

- take a task from CLI
- inspect a repo safely
- choose relevant files
- propose a clear plan
- edit files through controlled tools
- run tests or build commands
- retry after failures within limits
- produce a final summary
- produce a diff
- avoid destructive git operations without approval

---

## 14. Extension Priorities After v1

Recommended extension order:

1. reliability and guardrails
2. repo intelligence and summaries
3. better patching and repair loop
4. approval workflow
5. PR and issue integrations
6. dashboard / web UI
7. IDE extension
8. multi-agent specialization
9. container sandboxing
10. cloud/offline hybrid execution modes

---

## 15. Final Recommendation

Build the first real version as:

- **Python core agent**
- **OpenAI-compatible provider interface**
- **LM Studio as primary large-context backend**
- **Ollama as secondary local backend**
- **OpenAI as optional cloud backend**
- **CLI-first workflow**
- **safe tool-based execution**
- **state-driven orchestration**

The first milestone should be a reliable coding agent for bounded repo tasks, not a fully autonomous engineering system.