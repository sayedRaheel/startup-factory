**Product Requirements Document: Concept `agtop`**
**Owner:** Vera, Head of Product 
**Status:** Approved for immediate prototyping. No debates.

Listen up. The Scout report is painfully clear: developers are giving the keys to the kingdom to LLM agents, and these bots are quietly driving them into API bankruptcy while spinning in infinite regex loops. Nobody wants a heavy web dashboard or a Datadog integration just to see why `aider` or `gemini-cli` is hanging. They want an instant, cynical, low-level terminal tool.

We are building exactly three features. If anyone proposes a fourth feature, a SaaS tier, or a "cloud sync" option, I will personally revoke their repository access. 

Here is the PRD. Execute it.

---

### 1. Product Name
**`agtop`** (Agent Top)

### 2. Goal Alignment Trace
*   **I am proposing** a terminal-native, drop-in TUI profiler for LLM agents...
*   **Because** the Scout identified that developers are running agentic workflows entirely blind, bleeding API money to silent failures, hallucinated dependencies, and recursive tool-call loops...
*   **Because** our ultimate goal is to build viral, dependency-free open-source tools that farm GitHub stars by immediately solving acute, universal developer pain points without adding to their cognitive load.

### 3. One-Sentence Pitch
`htop` for AI agents: a razor-fast, zero-config terminal UI that visualizes token burn, tracks active tool calls, and auto-kills hallucinating local LLM processes before they drain your wallet.

### 4. The Target Audience
CLI-native software engineers, indie hackers, and AI tinkerers. These are users who run tools like `Aider`, `Claude CLI`, `Gemini CLI`, or custom LangChain/AutoGen scripts locally. They live in the terminal, despise JS bloat, and are terrified of waking up to a $500 OpenAI/Anthropic bill because a bot got stuck trying to `grep` a million-line log file.

### 5. Core Feature Set (Strictly 3)
1.  **The Live Burn Dashboard:** A localized TUI header displaying real-time token velocity (tokens/sec), absolute context-window saturation (e.g., `85k / 128k`), and estimated session cost in USD. No delayed logs—instant stdout/stderr stream parsing.
2.  **Tool-Call Trace Matrix:** A visual, chronological tree of what the agent is actually executing (e.g., `run_shell_command("npm install")` -> `read_file("package.json")`). It highlights repeated consecutive actions in red to instantly expose recursive hallucination loops.
3.  **The Wallet Guillotine (Kill-Switch):** Hard CLI flags (`--max-spend=0.50` or `--max-loops=3`) that automatically send a `SIGKILL` to the child agent process the millisecond it crosses a threshold. You press `k` to kill it manually.

### 6. Technical Stack Recommendation
*   **Language:** **Rust**. 
*   **Frameworks:** `ratatui` for the terminal UI. 
*   **Why:** We are targeting GitHub virality. Rust screams "blisteringly fast and memory-safe." It compiles down to a single, sub-5MB statically linked binary. No Node.js runtime, no Python virtual environments, no dependency hell. It drops in, it runs in microseconds, and it gets out of the way. 

### 7. User Flow (3 Steps)
1.  **Install:** `curl -sSfL https://agtop.sh | sh` (Installs the single Rust binary globally).
2.  **Wrap:** Instead of running the agent normally, the user prefixes their command: `agtop run --max-spend=2.00 -- "aider --message 'refactor the backend'"`
3.  **Monitor & Intervene:** The `agtop` TUI takes over the terminal. The user watches the agent's internal monologue, tool usage, and token burn rate in real time. If the bot gets stuck in a loop, the user hits `k` (or the `--max-spend` guillotine drops automatically), saving their codebase and their credit card. 

---
*No further discussion. Build the prototype.*
