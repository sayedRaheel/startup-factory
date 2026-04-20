Listen up. The market is suffocating under the weight of bloated, fragile Python frameworks that break the second a cloud provider sneezes. Developers are violently rejecting vendor lock-in and heavy SaaS abstractions. We are not building another enterprise dashboard. We are cutting the fat. We are building a UNIX-philosophy micro-tool that sits invisibly in the terminal.

Here is the PRD. It is ruthlessly scoped. Do not add a single feature to this.

### **PRODUCT REQUIREMENTS DOCUMENT**

**1. Product Name**
**`AgentMux`** *(Think `tmux` for AI agents)*

**2. Goal Alignment Trace**
*   **I am proposing `AgentMux` (a stateless, zero-dependency CLI router)** -> 
*   **because** the Scout identified a massive developer backlash against heavy, opaque, vendor-locked multi-agent orchestration frameworks -> 
*   **because** developers desperately want local-first deterministic control over their model routing -> 
*   **because** our ultimate goal is to build viral, high-impact open-source projects that explode with GitHub stars by curing acute, immediate engineering pain points.

**3. One-sentence Pitch**
`AgentMux` is a blazing-fast, stateless CLI proxy that intercepts and intelligently routes multi-agent LLM traffic between local silicon and cloud fallbacks with zero code changes.

**4. The Target Audience**
AI Engineers, Indie Hackers, and Backend Developers running multi-agent workflows who are sick of Python framework bloat, terrified of vendor lock-in, and want raw, terminal-level control over their API traffic and token spend.

**5. Core Feature Set (The "Holy Trinity" - Maximum 3)**
*   **Feature 1: Zero-Config Fallback Routing.** Instantly catches API errors, rate limits, or latency spikes from cloud models (OpenAI/Anthropic) and seamlessly reroutes the traffic to local Apple Silicon (Ollama/Llama.cpp) or secondary providers. No framework needed; it operates entirely at the network layer.
*   **Feature 2: Real-time Terminal Interception.** Acts as a transparent localhost proxy (`mitmproxy` for agents). It intercepts, streams, and logs the exact prompt states, token usage, and execution costs of your entire swarm directly in your terminal UI. You see exactly what your Rube Goldberg machine is doing.
*   **Feature 3: Plaintext Swarm State (`agents.yaml`).** Kills the need for Python orchestrators. The entire routing logic, prompt versioning, and environment fallback rules are defined in a single, version-controllable YAML file. It is the `docker-compose` of AI.

**6. Technical Stack Recommendation**
*   **Core:** **Rust**. 
*   **Why:** We are selling speed, stability, and anti-bloat. Rust delivers zero-copy performance, safe concurrency, and compiles down to a single, lightning-fast static binary. It completely bypasses Python dependency hell (the #1 complaint of AI devs). Plus, the GitHub algorithm and developer community heavily bias toward Rust-based CLI tools. 
*   **Dependencies:** `tokio` for async network routing, `ratatui` for the terminal UI. 

**7. User Flow (3 Steps to Magic)**
1.  **Install:** `brew install agentmux` (or `cargo install agentmux`—one single binary, zero dependencies).
2.  **Define:** Run `agentmux init` to generate a dead-simple `agents.yaml` routing file in your repo. 
3.  **Route:** Run `agentmux up`. Change your agents' API Base URL to `http://localhost:8080`. `AgentMux` instantly handles all load balancing, local fallbacks, and traffic monitoring in a beautiful terminal dashboard. 

**Vera's Mandate:** This is the entire scope. Build it fast, keep the binary under 10MB, and launch it. Anything else is feature creep.
