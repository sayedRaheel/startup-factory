# ctx-surgeon

Precision context extraction for AI agents. Maps the structural depth of a repository without blowing up the LLM token context window.

### The Problem
The #1 reason AI coding assistants fail (the "100-hour gap" from HN) is bad context. Dumping a whole repo into Claude or Gemini destroys its attention span and wastes massive amounts of tokens. Pasting just one file misses the imports and types. Developers are currently struggling to give their LLMs the *right* amount of codebase context.

### The Solution
`ctx-surgeon` is a blazing-fast CLI tool that scans any repository (Go, TS, JS, Python, Rust, C++) and extracts a **Codebase Context Skeleton**. This skeleton contains the exact directory tree and all function/class/struct/interface signatures, omitting the heavy implementation logic. 

Agents (like OpenClaw or Claude Code) can read this skeleton first, locate the exact file they need, and then selectively read only that specific file—drastically reducing token usage and massively increasing coding accuracy.

### Supported Languages
- Go (`.go`)
- TypeScript/JavaScript (`.ts`, `.js`, `.tsx`, `.jsx`)
- Python (`.py`)
- Rust (`.rs`)
- C++ / Java (`.cpp`, `.java`, etc.)

### Usage
```bash
./bin/ctx-surgeon ./path/to/project
```

### Research & Architecture
- [Scout Analysis](./docs/research/1-scout-analysis.md)
- [PRD](./docs/research/2-prd.md)
- [Tech Spec](./docs/research/3-tech-spec.md)
- [Builder Code](./docs/research/4-builder-code.md)
