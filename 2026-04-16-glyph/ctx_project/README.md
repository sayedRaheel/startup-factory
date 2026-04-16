# Ctx - Git for AI State

Ctx is a UNIX-style primitive that tracks your context and generates compressed context feeds for AI assistants.

### Problem Statement
AI orchestration frameworks are bloated and try to be everything. Ctx does one thing: it silently watches your file system, compresses your context, and composes via standard streams, with zero user configuration and instant startup.

### Features
- Silent background watcher (`ctx start`).
- Lightweight SQLite persistence.
- Output context via standard streams (`ctx feed`).
- Zero dependencies, single statically linked Rust binary.

### Research & Architecture
- [Scout Analysis](./docs/research/1-scout-analysis.md)
- [PRD](./docs/research/2-prd.md)
- [Tech Spec](./docs/research/3-tech-spec.md)
- [Builder Code](./docs/research/4-builder-code.md)
