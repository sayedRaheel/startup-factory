Listen up. I don't care about a "comprehensive suite of LLM management tools." That’s enterprise bloatware and it goes straight to the graveyard. 

Developers are bleeding right now. They are handing over the keys to their repositories to opaque AI agents that are quietly burning their API budgets and rewriting their architectures in the dark. We are going to build the exact tourniquet they need. Nothing more, nothing less. 

Here is the strict PRD. We ship this in two weeks.

***

# PRODUCT REQUIREMENTS DOCUMENT

### 1. Product Name
**`Curb`** 
*(Tagline: Keep your AI agents on a leash.)*

### 2. Goal Alignment Trace
*   **I am proposing** a universal, terminal-native interceptor and circuit breaker for AI CLI agents...
*   **-> Because** the Scout identified that engineers are terrified of opaque, autonomous bots silently mutating their local environments, trapping them in loops, and burning massive API credits...
*   **-> Because** our ultimate goal is to build a hyper-viral, zero-friction developer tool that hits #1 on GitHub Trending by directly resolving the most immediate, bleeding-neck anxiety in the AI engineering space today.

### 3. One-Sentence Pitch
`Curb` is a universal CLI middleware that wraps any autonomous AI coding agent, providing a real-time terminal HUD for cost-tracking and a dead-man’s switch that intercepts dangerous file mutations before they happen.

### 4. Target Audience
Senior/Staff engineers, indie hackers, and open-source maintainers who actively use CLI-based AI agents (like Claude Code, Aider, Open-SWE) but absolutely refuse to blindly trust a black-box LLM with their production codebases or their wallets.

### 5. Core Feature Set (The "Holy Trinity")
*Do not add to this list. If it isn't one of these three things, it is out of scope.*

1.  **The Interceptor HUD (Real-Time Telemetry):** A beautiful, terminal-native dashboard that wraps the standard agent output. It passively intercepts I/O to display live token-burn, cumulative session cost, and a scrolling ticker of the exact tools/shell commands the agent is currently executing.
2.  **The Circuit Breaker (Auto-Pause):** Configurable tripwires. If the agent hits a specific context threshold (e.g., `$2.00 burned`) or attempts a destructive action (e.g., `rm -rf`, bulk file rewrites, modifying `.env`), `Curb` forcefully pauses the execution thread instantly.
3.  **Glass-Wall Override (Human-in-the-Loop):** When a circuit breaker trips, the terminal immediately drops the user into an interactive TUI prompt. The developer can inspect the exact payload the agent is trying to execute, hit `[Y]` to approve, `[N]` to deny, or type a hard-override prompt to steer the agent back on track.

### 6. Technical Stack Recommendation
**Go (Golang) + Charmbracelet (`Bubble Tea` / `Lip Gloss`)**
*   **Why:** We are not building a bloated Electron app or an over-engineered Node daemon. Go produces a lightning-fast, single, statically compiled binary with zero dependencies. Charmbracelet’s TUI libraries are universally recognized as the sexiest, most viral terminal aesthetics on GitHub right now. It screams "modern developer tooling."

### 7. User Flow (Time-to-Value in < 30 Seconds)
1.  **Install:** `brew install curb`
2.  **Wrap & Run:** Prefix your normal agent command with `curb` and set your guardrails. 
    *(e.g., `curb --budget=$5.00 --protect="src/**/*.ts" -- claude-code`)*
3.  **Observe & Approve:** Watch the beautiful TUI track the agent's brain in real-time. When the agent tries to rewrite a protected file or gets stuck in a loop, hit `[Y]` or `[N]` to keep it moving or shut it down.

***
**Vera's Note:** No analytics. No accounts. No cloud syncing. Single binary. Maximum leverage. Get to work.
