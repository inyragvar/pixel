# TODO

## Goal

Turn the current scaffold into a reliable local-first development agent that can:
- inspect a repository
- select relevant files
- edit safely
- run validation commands
- iterate on failures
- present a clean final diff and summary

---

## Current state summary

Already done:
- [x] Python project scaffold
- [x] provider abstraction
- [x] OpenAI-compatible provider implementation
- [x] bounded action loop
- [x] planner + reviewer scaffolding
- [x] basic tools: files, search, shell, git
- [x] provider fallback chain:
  - [x] native tool calling
  - [x] JSON-schema response format
  - [x] plain JSON fallback
- [x] loop/action tests

Still missing for a solid v1:
- [ ] safer editing strategy
- [ ] safer execution strategy
- [ ] provider-specific behavior tuning
- [ ] better codebase retrieval
- [ ] persisted runs and replay/debugging

---

## Phase 1 — harden the current loop

### 1. Provider-specific adapter split
- [x] split `OpenAICompatibleProvider` behavior into capability-aware paths
- [x] add explicit provider config for:
  - [x] LM Studio
  - [x] Ollama
  - [x] OpenAI cloud
- [x] define capability flags such as:
  - [x] supports_native_tools
  - [x] supports_json_schema
  - [x] supports_beta_parse
  - [x] supports_streaming
- [x] handle provider-specific message/response quirks cleanly
- [x] add tests for each provider mode using fake clients

### 2. Action generation robustness
- [x] support malformed tool arguments more defensively
- [x] validate tool name against allowed tools before execution
- [x] add repair pass for invalid decisions
- [x] improve fallback prompting for weaker local models
- [x] log which provider fallback path was used during each decision

### 3. Better executor safety
- [x] reject unknown tool names before dispatch
- [x] validate required tool arguments before execution
- [x] limit file size for read/write operations
- [x] limit search result count and payload size
- [x] normalize command output for easier review by the model

---

## Phase 2 — improve editing

### 4. Patch-first editing
- [x] add unified diff patch application tool
- [x] prefer patch application over full-file rewrite
- [x] keep `write_file` for new files or explicit full rewrites only
- [x] capture patch failures with precise error output
- [x] add tests for patch application and rollback flow

### 5. Safer file operations
- [ ] add allowlist / denylist for editable paths
- [ ] block binary file writes by default
- [x] add backup/rollback for file edits during one run
- [ ] track before/after file hashes

---

## Phase 3 — improve code understanding

### 6. Repo map integration
- [ ] feed repo map summaries into the main loop automatically
- [ ] store architecture summaries per run
- [ ] include likely entrypoints / build commands in context

### 7. Better retrieval
- [ ] add symbol-aware search
- [ ] add import/reference summaries
- [ ] add optional embeddings-based semantic retrieval
- [ ] rank files before reading them into context

### 8. Large-context strategy
- [ ] define a context packing strategy for 32k / 128k / 200k models
- [ ] separate planning context from edit context
- [ ] avoid passing large transcripts when a compact state summary is enough

---

## Phase 4 — safer execution environment

### 9. Workspace isolation
- [ ] create a per-task temp workspace or git worktree
- [ ] support copying or cloning the target repo into a run directory
- [ ] keep artifacts per run:
  - [ ] logs
  - [ ] prompts
  - [ ] tool calls
  - [ ] diffs
  - [ ] command outputs

### 10. Sandbox
- [ ] add Docker-based command runner
- [ ] add CPU / memory / timeout limits
- [ ] add optional network isolation
- [ ] support project-specific execution images

### 11. Approval gates
- [ ] require approval for:
  - [ ] destructive file ops
  - [ ] git commit
  - [ ] git push
  - [ ] long-running shell commands
- [ ] add CLI approval UX

---

## Phase 5 — usability

### 12. CLI improvements
- [ ] richer run output formatting
- [ ] `--json` mode for automation
- [ ] resume failed run by ID
- [ ] show exact fallback mode used per decision
- [ ] show step budget and token/debug stats

### 13. Logging and persistence
- [ ] persist runs to JSONL or SQLite
- [ ] store final summaries and outcomes
- [ ] support replaying a past run for debugging
- [ ] redact secrets from stored logs

### 14. Streaming
- [ ] add streaming provider support where available
- [ ] stream reasoning-free progress updates to CLI
- [ ] show live tool calls and observations

---

## Phase 6 — validation and quality

### 15. Validation pipeline
- [ ] detect project type and choose default validation commands
- [ ] add configurable validation profiles:
  - [ ] Python
  - [ ] Node
  - [ ] Go
  - [ ] Rust
- [ ] support lint + tests + typecheck as separate steps

### 16. Reviewer improvements
- [ ] add explicit fix-verification step before finalize
- [ ] reviewer should inspect git diff, command outputs, and changed files
- [ ] detect likely incomplete work before returning final answer

### 17. Eval harness
- [ ] create small benchmark tasks for the scaffold repo
- [ ] measure:
  - [ ] task success rate
  - [ ] average steps used
  - [ ] validation pass rate
  - [ ] diff size
  - [ ] fallback mode frequency

---

## Phase 7 — external integrations

### 18. GitHub / GitLab
- [ ] issue ingestion
- [ ] PR summary generation
- [ ] comment drafting
- [ ] branch / commit message helpers

### 19. Editor integration
- [ ] VS Code integration
- [ ] diff preview and approval workflow
- [ ] apply selected changes only

### 20. Optional web UI
- [ ] run history dashboard
- [ ] live task trace
- [ ] config editor for providers/models

---

## Nice-to-have later

- [ ] multi-agent mode
- [ ] separate fast planner / coder / reviewer models
- [ ] semantic memory across projects
- [ ] issue-specific long-term memory
- [ ] automatic PR creation after approval

---

## Recommended next task

The best next implementation task is:

**add patch-first editing with unified diff application and rollback-friendly file tracking.**

That will make code edits safer and move the agent closer to a practical v1 for real repositories.
