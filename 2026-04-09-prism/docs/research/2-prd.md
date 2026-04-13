This is Vera. Listen up. 

Dr. Silas gave us the signal, and the market is bleeding. Developers are tearing their hair out trying to babysit AI agents that hallucinate, blow up context windows, and destroy codebases. We are not building another bloated enterprise execution framework. We are not building an LLM wrapper. 

We are building a surgical, zero-dependency micro-tool that solves exactly one problem perfectly. We are going to own the standard for local AI context. 

Here is the cut-throat PRD. No feature creep. No bloat. Just viral execution.

***

# PRODUCT REQUIREMENTS DOCUMENT

### 1. Product Name
**Tether** (`tether-cli`)

### 2. Goal Alignment Trace
*   **I am proposing** a lightning-fast, zero-dependency CLI that auto-scaffolds universal context boundaries and memory architectures for local codebases...
*   **-> because** the Scout identified that developers are wasting hours writing hacky, monolithic `CLAUDE.md` files and battling generalist AI agents that lack rigid, repository-specific scope...
*   **-> because** our ultimate goal is to build viral projects that get GitHub stars, and developers aggressively star drop-in, frictionless dev-ex tools that instantly fix the most painful friction point of the hottest current trend (local AI coding).

### 3. One-sentence Pitch
A lightning-fast, single-binary CLI that scaffolds standardized context boundaries and architectural maps to instantly sandbox, steer, and tame any local AI coding agent.

### 4. The Target Audience
Pragmatic engineers and open-source maintainers using tools like Aider, Claude Code, Cursor, or OpenDevin who are exhausted by AI hallucinations, massive context costs, and having to manually prompt architectural rules every single session.

### 5. Core Feature Set (Maximum 3)
*If an idea isn't on this list, it doesn't ship.*

1.  **Instant Stack Profiling & Scaffolding (`tether init`):** Scans the repository in milliseconds, identifies the stack, and generates a standardized `.agentrc` and `.github/SKILLS.md` manifest. It dictates the exact rules of engagement, formatting, and boundary restrictions the AI must follow.
2.  **Dynamic Context Mapping (`tether map`):** Automatically generates a lightweight, token-optimized architecture graph (`.agent-context.md`). Instead of the AI blindly reading 50 files and blowing up the context window, Tether gives it the exact dependency map and file definitions upfront. 
3.  **Agnostic Agent Injection:** Tether doesn't run the LLM. It generates universal, strictly formatted Markdown/JSON that Cursor, Aider, and Copilot naturally ingest as system prompts. It works with *everything* by standardizing the environment, not the engine.

### 6. Technical Stack Recommendation
**Rust.** 
We are optimizing for Hacker News/GitHub virality and developer trust. Rust gives us a blisteringly fast, memory-safe tool that compiles down to a **single, zero-dependency binary**. Developers will not install a 500MB Node.js framework just to manage `.md` files. We use `clap` for the CLI and `ignore` for instantaneous, git-aware directory traversal.

### 7. User Flow 
*Time to value must be under 15 seconds.*

1.  **Install:** `curl -sSf https://tether.sh | sh` (Drops the single binary into their path).
2.  **Initialize:** Run `tether init` in any repository. It maps the codebase and drops the `.agentrc` and context constraints into the project root.
3.  **Execute:** Launch your BYO agent (`aider`, `claude`, etc.). The agent natively reads the Tether constraints, stays strictly within bounds, and executes perfectly. 

***
**Vera's Final Note:** We do not add a UI. We do not add API keys. We build the definitive standard for local AI guardrails. Ship it.
