# Vise

The `.editorconfig` for Agentic Determinism. Vise is a pipe. It takes local state, pushes it through an LLM, and pipes the diff back. No chat. No markdown parsing errors. Just pure, deterministic output validated by your toolchain.

### Usage

```bash
# Initialize constraints
vise init

# Run a prompt
vise "Refactor the authentication middleware to use standard library context."
```

### Research & Architecture

* [Scout Analysis](../docs/research/1-scout-analysis.md)
* [PRD](../docs/research/2-prd.md)
* [Tech Spec](../docs/research/3-tech-spec.md)
* [Builder Code](../docs/research/4-builder-code.md)
