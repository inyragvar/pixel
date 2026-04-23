## Examples
```bash
dev-agent --task "Inspect this repository and propose the best next change" --provider lmstudio --model qwen/qwen3-coder-30b --workspace .

dev-agent --task "Find the current CLI entrypoint, explain how the app starts, and suggest one cleanup" --provider lmstudio --model qwen/qwen3-coder-30b --workspace .

dev-agent --task "Read the project structure and update README.md to match the actual current functionality, then show the summary of changes" --provider lmstudio --model qwen/qwen3-coder-30b --workspace .

dev-agent --task "Search for outdated references to OPENAI_API_BASE and replace them with wording that explains support for both OPENAI_BASE_URL and OPENAI_API_BASE" --provider lmstudio --model qwen/qwen3-coder-30b --workspace .

dev-agent --task "Find TODO items already implemented in code and update TODO.md to mark them done" --provider lmstudio --model qwen/qwen3-coder-30b --workspace .

dev-agent --task "Inspect provider code and refactor duplicated capability checks into one helper if possible, then run tests" --provider lmstudio --model qwen/qwen3-coder-30b --workspace .

dev-agent --task "Add a small unit test for workspace isolation cleanup behavior and run pytest" --provider lmstudio --model qwen/qwen3-coder-30b --workspace .

dev-agent --task "Find the filesystem safety logic and add a test that binary files are rejected for patching, then run pytest" --provider lmstudio --model qwen/qwen3-coder-30b --workspace .

dev-agent --task "Look for dead code or unused imports in the project and make safe cleanup changes, then run pytest" --provider lmstudio --model qwen/qwen3-coder-30b --workspace .

dev-agent --task "Inspect the current CLI options and improve the README usage examples so they are correct for the actual implementation" --provider lmstudio --model qwen/qwen3-coder-30b --workspace .

```

## Good - bad - 2026-04-23
What it is good at now:

- repo inspection
- documentation fixes
- small refactors
- test additions
- safe text-file edits
- patch-based changes
- running commands like pytest, grep, ls

What not to ask it yet:

 - push to git remote
 - complex multi-step architectural rewrites
 - binary file changes
 - arbitrary dangerous shell operations
 - editor integration tasks
 - tasks requiring persistent run history or resume support