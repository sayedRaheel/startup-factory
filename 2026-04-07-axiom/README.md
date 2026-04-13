# Warden

Ephemeral execution firewall for local agents. Warden isolates agent workflows using Git worktrees, verifies them through a user-provided command, and safely merges only successful attempts.

### Problem Statement
Running autonomous LLM agents against local codebases is dangerous. They frequently overwrite working logic with hallucinated dependencies, make unverified breaking changes, and corrupt state. We need a zero-dependency, globally installable firewall that confines agents to verified sandboxes and merges changes strictly upon test success.

### Research & Architecture
* [Scout Analysis](./docs/research/1-scout-analysis.md)
* [PRD](./docs/research/2-prd.md)
* [Tech Spec](./docs/research/3-tech-spec.md)
* [Builder Code](./docs/research/4-builder-code.md)
