# Curb

Curb is a high-performance proxy tool for local AI agents. It wraps around CLI agents like Claude-Code or Aider to provide a strict, stateless perimeter preventing accidental destruction or uncontrolled cloud spending.

### Problem Statement

The current state of autonomous AI tooling is a sandbox without walls. Unbounded agents have unrestricted access to local environments and no inherent limits on API spend, risking both system integrity and financial cost.

### Implementation Details

Curb intercepts the PTY stream between the user's terminal and the agent, matching the standard output against regex-based rules to enforce constraints. If a dangerous pattern is detected, execution is halted, and the user must explicitly approve the action via a sleek terminal UI.

### Research & Architecture

* [Scout Analysis](./docs/research/1-scout-analysis.md)
* [PRD](./docs/research/2-prd.md)
* [Tech Spec](./docs/research/3-tech-spec.md)
* [Builder Code](./docs/research/4-builder-code.md)
