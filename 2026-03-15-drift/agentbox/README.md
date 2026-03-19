# AgentBox

AgentBox is an ultra-lightweight CLI sandbox that wraps existing autonomous AI agents to enforce zero-trust execution, manage encrypted state, and cloak credentials.

### Problem Statement
Running autonomous AI agents locally often provides them unrestricted access to the host's file system, environment variables, and execution context. This poses significant risks, including accidental file destruction, unintended system changes, and exposure of sensitive API keys or credentials. A simple, zero-configuration sandbox is needed to wrap untrusted agent execution without the overhead of heavy virtualization or complex container configurations.

### Research & Architecture
* [Scout Analysis](./docs/research/1-scout-analysis.md)
* [PRD](./docs/research/2-prd.md)
* [Tech Spec](./docs/research/3-tech-spec.md)
* [Builder Code](./docs/research/4-builder-code.md)

### Installation & Usage

# Initialize the secure context and configuration
agentbox init

# Run an agent command through the sandbox
agentbox run <command>
