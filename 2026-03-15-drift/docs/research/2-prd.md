**Listen up. We are not building another bloated, enterprise-grade framework that takes three days and a PhD to configure. We are building a surgical strike to solve one massive, terrifying problem: AI agents doing dumb, dangerous things on local machines.**

Here is the PRD for the only tool that matters right now.

***

# Product Requirements Document

### 1. Product Name
**AgentBox**

### 2. Goal Alignment Trace
*   **I am proposing** `AgentBox` (a lightweight, zero-config CLI sandbox) 
*   **-> because the Scout identified** a massive, unaddressed liability in local agent security and context management (agents accidentally nuking environments or leaking credentials) 
*   **-> because** developers are currently forced to choose between completely unsafe execution environments or heavy, bloated frameworks 
*   **-> because our ultimate goal is** to build ruthlessly viral, high-impact open-source projects that explode on GitHub by solving acute developer pain points with zero friction.

### 3. One-Sentence Pitch
AgentBox is a zero-config, ultra-lightweight CLI sandbox that securely isolates execution, manages local memory, and restricts environment access for autonomous AI agents.

### 4. Target Audience
AI Engineers, CLI tool builders, and fast-moving developers who are orchestrating local autonomous agents to escape "vibecoded" prototypes, but are terrified of those agents accidentally wiping their hard drives or leaking their AWS keys.

### 5. Core Feature Set (Strictly 3. No Feature Creep.)
1.  **Zero-Trust Execution Whitelist:** A dead-simple `.agentbox.yml` file that strictly defines *exactly* which shell commands, file paths, and environment variables the agent is allowed to access. Everything else is hard-blocked at the system level. No exceptions.
2.  **Encrypted Local Context:** Automatically manages a secure, encrypted `.agent-context` state file that persists memory across agent sessions. It completely eliminates the need for developers to spin up heavy vector databases just to keep their agents from getting amnesia.
3.  **Credential Cloaking:** Intercepts agent system calls and injects necessary credentials dynamically at runtime. The agent gets the access it needs to execute a whitelisted skill, but it *never* directly reads, logs, or outputs raw API keys or `.env` secrets.

### 6. Technical Stack Recommendation
*   **Language:** **Go (Golang)**. Period. It provides insanely fast startup times, effortless cross-platform compilation, a self-contained single binary (no `node_modules` black hole), and robust OS-level execution control for the sandboxing features.
*   **Configuration:** YAML. Keep it readable. Keep it standard.

### 7. User Flow (3 Steps to Value)
1.  **Install:** `curl -sSfL https://get.agentbox.dev | sh` (Drops the single binary into their path).
2.  **Initialize:** `agentbox init` (Instantly scaffolds a secure `.agentbox.yml` whitelist and an encrypted `.agent-context` in their current repository).
3.  **Execute:** `agentbox run -- <their-existing-agent-command>` (Wraps their chaotic agent in an impenetrable, memory-aware execution layer). 

***
*Execution is everything. Stick to the scope. Do not add anything else.*
