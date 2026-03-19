# agtop

The aggressively lightweight TUI dashboard and network interceptor for LLM Agents. 

`agtop` runs your agent in a subprocess, intercepts network calls to OpenAI/Anthropic APIs by dynamically injecting endpoints, and forces the agent to wait for your approval in a beautiful terminal UI before generating tokens.

## Usage

agtop python main.go
agtop node agent.js

### Research & Architecture

* [Scout Analysis](./docs/research/1-scout-analysis.md)
* [PRD](./docs/research/2-prd.md)
* [Tech Spec](./docs/research/3-tech-spec.md)
* [Builder Code](./docs/research/4-builder-code.md)
