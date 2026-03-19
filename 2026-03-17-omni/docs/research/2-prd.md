Listen to me. Feature creep is the death of virality. If you build another heavy, bloated GraphRAG agent framework, you will be laughed off GitHub. Developers don't want more infrastructure; they want their AI to stop being stupid and forgetful. 

We are stripping this down to the absolute bare metal. No heavy vector databases. No Docker containers. Just a ruthless, lightweight binary that solves the exact pain point Dr. Silas identified, seamlessly. 

Here is the PRD. Nothing more, nothing less.

***

# PRODUCT REQUIREMENTS DOCUMENT

### 1. Product Name
**Engram** 

### 2. Goal Alignment Trace
*   **I am proposing** the creation of Engram, a zero-config, headless memory daemon...
*   **...because the Scout identified** that developers are bleeding hours babysitting fast but forgetful AI coding agents, acting as full-time reviewers for their own AI's lost context...
*   **...because our ultimate goal is** to build a highly-focused, viral open-source project that skyrockets to #1 on GitHub by eliminating the single most crushing friction point in modern AI dev workflows.

### 3. One-Sentence Pitch
Engram is a zero-config, invisible background daemon that acts as a persistent flight recorder for your codebase, automatically capturing and compressing project state so your AI agents never forget your architecture, past mistakes, or active context.

### 4. Target Audience
High-velocity engineers and early adopters using AI dev tools (Cursor, Claude Code, Aider, Copilot) who are aggressively fatigued by copying and pasting architectural rules and terminal errors into prompt windows.

### 5. Core Feature Set (The "Viral 3")
*If anyone suggests a fourth feature, I will personally fire them.*

1.  **The Invisible Flight Recorder (Passive Daemon):** 
    A microscopic background watcher that tails terminal outputs, Git diffs, and filesystem events. It silently records what you and the AI are *actually* doing, without you ever having to manually log a thing. 
2.  **Token-Crushing Compression Engine:** 
    No bloated local LLMs or chunky vector DBs. Engram uses deterministic text summarization and AST parsing to aggressively compress massive session histories and architectural rules into highly dense, token-optimized Markdown.
3.  **Instant Injection (`engram dump`):** 
    A single command that spits out the perfectly formatted, hyper-relevant context of your current session directly into your clipboard (or a `.cursorrules` / `.agent-context` file) ready for the AI to ingest instantly. 

### 6. Technical Stack Recommendation
*   **Core Language:** **Rust.** (It is GitHub catnip. It guarantees a single, insanely fast, zero-dependency binary with a non-existent memory footprint—perfect for a background daemon).
*   **Storage:** **SQLite.** (Embedded, zero-config, hyper-fast. We do not require users to spin up external databases).
*   **Parsing:** **Tree-sitter.** (Fast, robust AST parsing to understand code changes without heavy AI models).

### 7. User Flow (3 Steps to Magic)
1.  **Install:** `curl -sL https://engram.run/install.sh | bash` (Drops a single Rust binary onto their system).
2.  **Ignite:** Run `engram start` in any directory. It drops a `.engramignore`, spawns the silent daemon, and gets out of your way. 
3.  **Leverage:** Code normally. When your AI loses the plot or you start a fresh chat, type `engram dump`. The exact state of the project, recent errors, and architectural context are piped straight into the agent.
