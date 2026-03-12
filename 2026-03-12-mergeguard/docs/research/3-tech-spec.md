## MergeGuard Technical Specification

### Architecture
- **Language:** TypeScript
- **Runtime:** Node.js (v18+)
- **LLM Provider:** OpenAI API (gpt-4-turbo or gpt-3.5-turbo)
- **Git Interfacing:** `simple-git` for Node to reliably extract local diffs.

### System Flow
1. User runs `npx mergeguard review` locally, or it triggers via a GitHub Action.
2. System extracts uncommitted changes or the PR diff using `git diff HEAD`.
3. System reads the `.mergeguard.yml` rules file in the repository root.
4. Diff + Rules are compiled into a strict prompt template and sent to the LLM.
5. The parsed JSON response is formatted and printed to `stdout` with colorized severity levels (Error, Warning, Nitpick).
