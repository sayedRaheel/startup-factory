<div align="center">
  <img src="./banner.png" alt="ZeroPM Banner" width="800">
  <h1>ZeroPM</h1>
  <p>A ruthless, local-first CLI orchestrator designed to completely automate your software development process.</p>
</div>

---

## The Problem
The era of clicking through 40 fields in Jira to assign a ticket to an AI is dead. Enterprise SaaS orchestrators are bloated, expensive, and fundamentally misunderstand the workflow of the modern, agent-empowered developer. 

Right now, developers are forced to manually babysit and prompt-chain their local AI agents, dealing with soul-crushing administrative overhead instead of actually writing code. 

## What is ZeroPM?
Meet ZeroPM—a terminal-native orchestrator. ZeroPM reads your raw Markdown PRD, generates a dependency-aware task graph via OpenAI Structured Outputs, and autonomously executes the shell commands required to build the software. 

No web UI. No cloud syncing. No feature creep. Just a razor-sharp tool that builds exactly what is needed, and nothing else. Consider your project manager officially fired.

## Target Audience
Built exclusively for elite 10x engineers, indie hackers, and hyper-productive open-source maintainers who despise manual task breakdown and context-switching.

## Key Features

### The DAG Compiler (Markdown-to-Graph)
ZeroPM ingests a single, raw `PRD.md` or feature request from your repo and instantly shatters it into a sequence of atomic, executable shell commands using the `gpt-4o` API.

### The Autonomous Dispatcher
ZeroPM executes the generated commands sequentially in your local environment. If a task fails (non-zero exit code), the orchestrator instantly halts, printing the exact error trace so you can intervene. 

## Technical Stack
ZeroPM is built with **Go (Golang)** for cross-platform compilation, lightning-fast execution, and zero dependencies. 

Say goodbye to Python environment hell or the `node_modules` black hole. Build it once, run it anywhere.

---

## Quick Start
If it takes more than 3 steps to get value, we've failed. Here is your 3-step viral loop:

### 1. Build from Source
Zero external libraries. Just standard Go.
```bash
git clone https://github.com/sayedRaheel/startup-factory.git
cd startup-factory/2026-03-13-zeropm/zeropm
go build -o zeropm main.go
sudo mv zeropm /usr/local/bin/
```

### 2. Define
Drop a `PRD.md` file into the root of your target repository. For example:
```markdown
# My App
Please initialize a new Node project, install express, and create a basic server.js file that listens on port 3000.
```

### 3. Nuke It
Export your API key, then run the execute command. The terminal lights up as ZeroPM builds the execution graph and spins up the shell commands autonomously. You do nothing but watch.
```bash
export OPENAI_API_KEY="sk-..."
zeropm execute PRD.md
```
