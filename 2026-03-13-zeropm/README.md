
# ZeroPM

## The Problem
The era of clicking through 40 fields in Jira to assign a ticket to an AI is dead. Enterprise SaaS orchestrators are bloated, expensive, and fundamentally misunderstand the workflow of the modern, agent-empowered developer. Right now, developers are forced to manually babysit and prompt-chain their local AI agents, dealing with soul-crushing administrative overhead instead of actually writing code. 

## Introduction
Meet ZeroPM—a ruthless, local-first CLI orchestrator designed to completely automate your software development process. ZeroPM reads your Markdown PRD, generates a dependency-aware task graph, and autonomously dispatches your local AI agents to build the software. 

No web UI. No cloud syncing. No feature creep. Just a razor-sharp, terminal-native tool that builds exactly what is needed to orchestrate local agents, and nothing else. Consider your project manager officially fired.

## Target Audience
Built exclusively for elite 10x engineers, indie hackers, and hyper-productive open-source maintainers who already use CLI AI coding agents (like Claude Code, OpenClaw, or Aider) but absolutely despise manual task breakdown, project management, and context-switching.

## Core Features

### The DAG Compiler (Markdown-to-Graph)
ZeroPM ingests a single, raw `PRD.md` or feature request from your repo and instantly shatters it into a Directed Acyclic Graph (DAG) of granular, executable sub-tasks. No databases to configure, no forms to fill out.

### The Dispatcher (Agent Handoff)
Natively hooks into existing CLI AI agents via standard I/O. It feeds the exact, context-scoped sub-task to the agent (e.g., `aider --message "Implement the auth middleware"`), monitors the exit codes, and pipes the state forward to the next node in the graph when successful.

### The Auto-Resolver (Conflict Management)
As concurrent agents complete tasks, ZeroPM aggressively manages Git state, auto-committing successful nodes and attempting to auto-resolve merge conflicts between agent branches. It only interrupts the human user with a terminal prompt when an unresolvable collision occurs.

## Technical Stack
ZeroPM is built with Go (Golang) for cross-platform compilation, lightning-fast execution, native concurrency, and zero dependencies. 

Say goodbye to Python environment hell or the `node_modules` black hole. ZeroPM is distributed as a single, statically compiled binary that executes instantly.

### State Management
All state is managed via a local SQLite database tucked cleanly into a `.zeropm` hidden folder in your repository root. 

## Quick Start
If it takes more than 3 steps to get value, we've failed. Here is your 3-step viral loop:

### 1. Install
Zero dependencies. Instant availability.
```bash
curl -sL https://zeropm.dev/install | bash
```

### 2. Define
Drop a `PRD.md` file into the root of your target repository.

### 3. Nuke It
Run the execute command. The terminal lights up as ZeroPM builds the execution graph, spins up the local agents, and builds the software autonomously. You do nothing but review the final PR.
```bash
zeropm execute PRD.md
```

## Research & Architecture
- [Scout Analysis](./docs/research/1-scout-analysis.md)
- [Product Requirements Document (PRD)](./docs/research/2-prd.md)
- [Technical Specification](./docs/research/3-tech-spec.md)
- [Builder Code](./docs/research/4-builder-code.md)
```
