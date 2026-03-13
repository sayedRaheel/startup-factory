# Product Requirements Document (PRD)

**Author:** Vera, Strategist & Product Manager
**Status:** APPROVED FOR EXECUTION. ALL BLOAT WILL BE REJECTED AT COMPILE TIME.

Listen up. The era of clicking through 40 fields in Jira to assign a ticket to an AI is dead. Enterprise SaaS orchestrators are bloated, expensive, and fundamentally misunderstand the workflow of the modern, agent-empowered developer. We are building a razor-sharp, terminal-native tool. No web UI. No cloud syncing. No feature creep. We build exactly what is needed to orchestrate local agents, and nothing else.

Here is the blueprint. Execute it flawlessly.

### 1. Product Name
**ZeroPM**

### 2. Goal Alignment Trace
I am proposing **ZeroPM** -> *because* the Scout identified a critical gap where developers are forced to manually babysit and prompt-chain their local AI agents -> *because* our ultimate goal is to build a viral, frictionless open-source tool that prints GitHub stars by completely automating the soul-crushing administrative overhead of software development.

### 3. One-sentence Pitch
ZeroPM is a ruthless, local-first CLI orchestrator that reads your Markdown PRD, generates a dependency-aware task graph, and autonomously dispatches your local AI agents to build the software.

### 4. The Target Audience
Elite 10x engineers, indie hackers, and hyper-productive open-source maintainers who already use CLI AI coding agents (like Claude Code, OpenClaw, or Aider) but despise manual task breakdown, project management, and context-switching.

### 5. Core Feature Set (The "Holy Trinity")
Do not add a fourth feature. If you propose a fourth feature, I will close your PR.
1. **The DAG Compiler (Markdown-to-Graph):** ZeroPM ingests a single, raw `PRD.md` or feature request from your repo and instantly shatters it into a Directed Acyclic Graph (DAG) of granular, executable sub-tasks. No databases to configure, no forms to fill out. 
2. **The Dispatcher (Agent Handoff):** Natively hooks into existing CLI AI agents via standard I/O. It feeds the exact, context-scoped sub-task to the agent (e.g., `aider --message "Implement the auth middleware"`), monitors the exit codes, and pipes the state forward to the next node in the graph when successful.
3. **The Auto-Resolver (Conflict Management):** As concurrent agents complete tasks, ZeroPM aggressively manages Git state, auto-committing successful nodes and attempting to auto-resolve merge conflicts between agent branches. It only interrupts the human user with a terminal prompt when an unresolvable collision occurs.

### 6. Technical Stack Recommendation
**Go (Golang).** 
This must be a single, statically compiled binary that executes instantly. I will not tolerate Python environment hell or a `node_modules` black hole for a CLI tool. Go gives us cross-platform compilation, lightning-fast execution, native concurrency (goroutines are perfect for the DAG execution and dispatcher), and zero dependencies. 
*State Management:* Local SQLite database tucked cleanly into a `.zeropm` hidden folder in the repo root.

### 7. User Flow (The 3-Step Viral Loop)
If it takes more than 3 steps to get value, we've failed.

1. **Install:** `curl -sL https://zeropm.dev/install | bash` (Zero dependencies. Instant availability).
2. **Define:** The developer drops a `PRD.md` file into the root of their target repository.
3. **Nuke It:** The developer runs `zeropm execute PRD.md`. The terminal lights up as ZeroPM builds the execution graph, spins up the local agents, and builds the software autonomously. The developer does nothing but review the final PR. 

---
**Vera's Final Note:** Keep it lean. Keep it aggressive. We are selling the fantasy of firing your project manager. Build it exactly as specified.
