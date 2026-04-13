# vgrep - Vector Grep

### The Problem
The market is drowning in over-engineered "context layers" that take 10 minutes to ingest a single repository. We don't need a platform; we need a fast, local CLI that executes with mechanical precision to semantically search our codebase and pipe results directly into LLMs.

### Research & Architecture
* [Scout Analysis](./docs/research/1-scout-analysis.md)
* [PRD](./docs/research/2-prd.md)
* [Tech Spec](./docs/research/3-tech-spec.md)
* [Builder Code](./docs/research/4-builder-code.md)

### Usage
# Index the current codebase
./vgrep.py init .

# Search naturally
./vgrep.py search "database connection logic"

# Export XML for LLM piping
./vgrep.py search "how does the auth work" --prompt
