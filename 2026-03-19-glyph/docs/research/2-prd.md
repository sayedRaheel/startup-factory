Listen up. The era of building cute, thin AI wrappers is dead. If we want to dominate GitHub trending and Hacker News today, we don't build another agent—we build the pickaxes for the gold rush. Developers are deploying autonomous agents and watching their codebases get shredded while their API bills explode. They are flying blind.

We are going to build the exact tool they are begging for. No bloat. No enterprise dashboards. Just a ruthless, surgical CLI that gives them their control back. 

Here is the strict PRD. Execute it exactly.

***

### 1. Product Name
**`agtop`** (Agent Top)

### 2. Goal Alignment Trace
**I am proposing** a universal, real-time agent telemetry CLI (`agtop`) -> **because the Scout identified** that engineers are bleeding time baby-sitting opaque, hallucinating AI agents and losing track of massive token burn -> **because our ultimate goal** is to build massively viral, high-impact open-source tools that hit #1 on GitHub trending by solving immediate, bleeding-edge developer pain.

### 3. One-Sentence Pitch
`agtop` is an `htop`-style terminal dashboard that intercepts, visualizes, and debugs any autonomous AI agent's tool calls, token burn, and file-system operations in real time.

### 4. The Target Audience
Forward-thinking software engineers, indie hackers, and open-source maintainers who are actively running autonomous AI workflows locally (Claude Code, AutoGPT, custom LangGraph/CrewAI setups) and are sick of treating non-deterministic, expensive AI executions as a black box.

### 5. Core Feature Set
*We are shipping exactly three features. If someone suggests adding cloud sync, fire them.*

1.  **The `htop` TUI for Agents:** A ruthless, beautiful terminal UI providing live visualization of API cost burn rates, context-window saturation, and active tool execution streams. 
2.  **Universal Proxy Interception (Step-Through Debugging):** `agtop` wraps the execution environment to intercept network requests and shell/file commands *before* they execute. The user can press `Space` to pause the agent, inspect the exact payload/prompt, and approve or reject the action.
3.  **Deterministic File-System Rollback ("Ctrl-Z for Agents"):** `agtop` automatically caches a diff of any file *right before* an agent overwrites it. If the agent hallucinates and destroys a file, the developer hits `R` to instantly revert the specific rogue operation without needing to untangle their Git history.

### 6. Technical Stack Recommendation
**Go + Charmbracelet (Bubble Tea)**
*   **Why:** Go compiles to a single, lightning-fast cross-platform binary. It is the undisputed king of modern developer CLIs (like `gh`, `k9s`). Charmbracelet's `Bubble Tea` library will give us that stunning, viral, high-framerate terminal aesthetic that instantly gets upvoted on Hacker News.
*   **What we avoid:** No bloated Electron apps. No React dashboards. No Node.js dependency hell. Just `brew install agtop` and instant execution.

### 7. User Flow
1.  **Install:** `brew install agtop` (Downloads a single, zero-dependency binary).
2.  **Wrap:** The user prefixes their normal agent command with `agtop`, routing its execution through our proxy (e.g., `agtop run claude-code` or `agtop run python my_agent.py`).
3.  **Control:** The TUI instantly takes over the terminal. The user watches token burn tick up in real-time, intercepts a suspicious `rm -rf` tool call by pressing `Space` to deny it, and forces the agent to try a different path.
