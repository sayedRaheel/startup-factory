# AgentMux

A highly concurrent, single-binary Layer 7 HTTP proxy designed for LLM API load-balancing and fallback mechanisms. Built for speed and reliability, preventing dependency hell via a UNIX-philosophy design.

## Features

- **Single Binary**: No node_modules, no python environments.
- **Failover Routing**: Automatically reroutes 500s and 429s from primary APIs (like OpenAI) to fallbacks (like Ollama).
- **Live TUI**: Built-in telemetry dashboard for monitoring requests and fallbacks.

### Research & Architecture
* [Scout Analysis](./docs/research/1-scout-analysis.md)
* [PRD](./docs/research/2-prd.md)
* [Tech Spec](./docs/research/3-tech-spec.md)
* [Builder Code](./docs/research/4-builder-code.md)
