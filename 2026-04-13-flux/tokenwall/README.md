# TokenWall

TokenWall is a local API proxy built to intercept, modify, cache, and firewall JSON payloads destined for LLM providers (OpenAI/Anthropic). It sits directly on the critical path between your developer agents and the LLM, protecting your wallet and enforcing context efficiency without sluggish latency.

### The Problem
Kitchen-sink wrappers are dead. Developers are building automated agents that burn through token budgets uncontrollably. We need a surgical, localized proxy that acts as a true firewall—checking budgets, compressing massive conversational histories offline via Ollama, and strictly diffing local code context via semantic caching before the payload ever reaches a paid endpoint.

### Research & Architecture
* [Scout Analysis](./docs/research/1-scout-analysis.md)
* [PRD](./docs/research/2-prd.md)
* [Tech Spec](./docs/research/3-tech-spec.md)
* [Builder Code](./docs/research/4-builder-code.md)

### Features
- **Strict Budget Firewall:** SQLite-backed ledger enforcing hard daily limits.
- **Semantic File Caching:** Hashing local workspace files embedded in prompts to prevent re-sending identical context.
- **Ollama Context Distillation:** Offline memory compression of expansive histories using local open-weight models.
- **SSE Stream Interception:** Perfectly aligned token consumption tracking without breaking native client streams.
