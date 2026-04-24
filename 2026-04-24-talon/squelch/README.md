# Squelch

Squelch is the invisible middleware for local agent frameworks, operating as a stateless MCP server over stdio.

### Problem Statement
Token processing is the primary bottleneck for agent reasoning speed and cost. Squelch intercepts, truncates, and sanitizes massive outputs before they hit the context window, preventing architectural negligence.

### Research & Architecture
* [Scout Analysis](./docs/research/1-scout-analysis.md)
* [PRD](./docs/research/2-prd.md)
* [Tech Spec](./docs/research/3-tech-spec.md)
* [Builder Code](./docs/research/4-builder-code.md)
