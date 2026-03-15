<div align="center">
  <img src="./banner.png" alt="MergeGuard Banner" width="800">
  <h1>MergeGuard</h1>
  <p>An automated AI code reviewer that catches bugs and enforces style guidelines on your GitHub Pull Requests before human review.</p>
</div>

---

## The Problem
Engineering teams waste countless hours on tedious code reviews. Senior engineers are bogged down pointing out minor style violations, forgetting edge-case logic, or missing subtle security vulnerabilities because they are rushing through Pull Requests.

## What is MergeGuard?
MergeGuard is an automated, highly-intelligent pre-review CLI that hooks directly into your Git workflow. It analyzes your `git diff` using a configured LLM and enforces your project's custom rules before a human ever looks at the code.

## Key Features

### Intelligent Diff Analysis
MergeGuard automatically extracts your local uncommitted changes or PR diffs and compiles them into a highly optimized context window.

### Custom Rules Engine
Create a `.mergeguard.json` file in your repository. MergeGuard reads these custom instructions (e.g., "Always use `snake_case` for database models") and forces the AI to grade the diff specifically against your team's unique guidelines. If the code is dangerously flawed, it halts the commit.

### CI/CD Integration
Run it locally via the CLI to check your code before committing, or plug it seamlessly into a GitHub Action/Git Hook.

## Tech Stack
- **Language:** JavaScript (Node.js 18+)
- **LLM Client:** Native Fetch (Zero dependencies!)
- **Git Interfacing:** Native `child_process`

---

## Getting Started

### Prerequisites
- Node.js (v18 or higher)
- An active `OPENAI_API_KEY` set in your environment variables.

### Installation
You can run MergeGuard instantly without installing anything locally:
```bash
export OPENAI_API_KEY="sk-..."
npx mergeguard-ai
```

*(Alternatively, you can clone the repository to run it locally from source).*

```bash
git clone https://github.com/sayedRaheel/startup-factory.git
cd startup-factory/2026-03-12-mergeguard
npm link
mergeguard
```
