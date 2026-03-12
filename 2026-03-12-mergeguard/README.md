# MergeGuard

An automated AI code reviewer that catches bugs and enforces style guidelines on your GitHub Pull Requests before human review.

---

## The Problem
Engineering teams waste countless hours on tedious code reviews. Senior engineers are bogged down pointing out minor style violations, forgetting edge-case logic, or missing subtle security vulnerabilities because they are rushing through Pull Requests.

## What is MergeGuard?
MergeGuard is an automated, highly-intelligent pre-review CLI and GitHub Action that hooks directly into your Git workflow. It analyzes your `git diff` using a configured LLM and enforces your project's custom rules before a human ever looks at the code.

## Key Features

### Intelligent Diff Analysis
MergeGuard automatically extracts your local uncommitted changes or PR diffs and compiles them into a highly optimized context window, ensuring the LLM understands exactly what changed without hallucinating context.

### Custom Rules Engine
Drop a `.mergeguard.yml` file in your repository. MergeGuard reads these custom instructions (e.g., "Always use `snake_case` for database models") and forces the AI to grade the diff specifically against your team's unique guidelines.

### CI/CD Integration
Run it locally via the CLI to check your code before committing, or plug it seamlessly into a GitHub Action to automatically comment on PRs with line-by-line feedback.

## Tech Stack
- **Language:** TypeScript & Node.js
- **LLM Client:** Official OpenAI Node SDK
- **Git Interfacing:** `simple-git`

---

## Getting Started

### Prerequisites
- Node.js (v18 or higher)
- An active `OPENAI_API_KEY` set in your environment variables.

### Installation
You can run MergeGuard instantly without installing:
```bash
export OPENAI_API_KEY="sk-..."
npx mergeguard review
```

*(Alternatively, you can clone the repository to run it locally from source).*

---

## Research & Architecture

Our AI swarm generated this project based on real-time market gaps. Read the internal research here:
- [Scout Analysis](./docs/research/1-scout-analysis.md)
- [Product Requirements Document (PRD)](./docs/research/2-prd.md)
- [Technical Specification](./docs/research/3-tech-spec.md)
- [Builder Code](./docs/research/4-builder-code.md)
