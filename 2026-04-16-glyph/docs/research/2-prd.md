Listen up. I've read the Scout's gap analysis, and the mandate is clear: developers are drowning in context bloat and duct-tape agent frameworks. We are not building another heavyweight orchestrator, and we are absolutely not building a cloud platform. Feature creep is the death of virality. 

We are going to build a razor-sharp, zero-friction micro-tool that does exactly *one* thing perfectly: it cures AI amnesia without making the developer lift a finger. We strip out the garbage, we build it close to the metal, and we ship a native binary that developers will worship.

Here is the PRD. Execute it flawlessly.

***

# PRODUCT REQUIREMENTS DOCUMENT

### 1. Product Name
**`Ctx`** *(Pronounced: Context)* 
*Subtitle: Git for AI State.*

### 2. Goal Alignment Trace
*   **I am proposing** `Ctx`, an invisible, native micro-CLI that automatically compresses and injects dynamic project state...
*   **-> because** the Scout identified a visceral market pain where developers are bleeding hours fighting amnesiac agents, exhausting context windows, and manually maintaining massive `CLAUDE.md` files...
*   **-> because** our ultimate goal is to hit #1 on GitHub Trending by delivering an ultra-lightweight, high-impact tool that natively integrates into any developer's workflow with zero friction.

### 3. One-Sentence Pitch
A zero-config native binary that silently runs in the background to automatically track, compress, and inject semantic project context into any AI coding agent.

### 4. Target Audience
Senior engineers, prompt engineers, and hardcore terminal junkies who use CLI-based AI assistants (Aider, Claude CLI, Gemini) or local models, and are completely sick of manual copy-pasting, context window exhaustion, and flaky agent frameworks.

### 5. Core Feature Set (Strictly 3 Features. Do not add more.)
1.  **The Silent Daemon (Zero-Config Watcher):** No `.json` configs. No dashboards. `Ctx` runs invisibly in the background, continuously tracking `git diffs`, terminal commands, and file saves, structuring them into a rolling local graph of the developer's immediate intent.
2.  **Auto-Compression Engine:** We do not blindly dump files into the prompt. `Ctx` automatically prunes stale state and compresses recent activity into a token-optimized semantic summary, ensuring the LLM gets *exactly* what it needs without hallucinating or blowing up context limits.
3.  **Universal Injection Pipe (`ctx feed`):** Complete agnostic compatibility. `Ctx` outputs raw, token-optimized context to standard output. Developers can pipe it into literally anything: `ctx feed | aider`, `cat $(ctx file) >> prompt.txt`, or bind it to a Neovim macro. 

### 6. Technical Stack Recommendation
*   **Language:** **Rust**. It screams "native, fast, and zero bloat." We want a single standalone binary. No Python virtual environments. No Node.js dependency hell. 
*   **Local Storage:** Embedded **SQLite**. Fast, robust, zero-setup.
*   **Distribution:** Raw binaries via `curl`, Homebrew, and Cargo. 

### 7. User Flow (3 Steps to Magic)
1.  **Install:** `curl -sL ctx.sh | bash` *(Downloads the binary and boots the silent watcher).*
2.  **Work:** The developer writes code, runs tests, and uses git normally. `Ctx` silently builds the memory state in the background. No manual logging required.
3.  **Inject:** When the AI agent goes off the rails or needs context, the developer runs `ctx inject aider` (or simply pipes `ctx get | llm`). The agent instantly "remembers" the entire session structure and intent.

***
**Vera's Final Note:** 
Do not add a GUI. Do not add an API server. Keep the surface area tiny and the utility massive. Build the core loop, make the binary under 10MB, and get it on GitHub. Now get to work.
