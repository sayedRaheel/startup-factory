**Listen up. We are not building another bloated, telemetry-riddled IDE.** The market is suffocating on wrapped SaaS products disguised as developer tools. Developers want raw power, absolute privacy, and zero friction. We are building a surgical instrument, not a Swiss Army knife.

Here is the finalized Product Requirements Document.

***

### 1. Product Name
**`Siphon`** 
*(Short, visceral, implies pulling fluid data from one source to another without spillage.)*

### 2. Goal Alignment Trace
*   **I am proposing** a lightning-fast, zero-config CLI translation layer for codebase context...
*   **-> because** the Scout identified that developers are currently wasting hours writing fragile duct-tape scripts just to wire their local codebases to headless, memory-constrained edge LLMs (Ollama, LM Studio)...
*   **-> because** our ultimate goal is to build a viral, high-utility developer tool that dominates GitHub trending by tapping into the explosive demand for private, offline, UNIX-native AI workflows.

### 3. One-sentence Pitch
**`Siphon`** is a lightning-fast Rust binary that acts as the ultimate UNIX pipe for offline AI—violently compressing your entire repository into a token-optimized stream for local edge models.

### 4. The Target Audience
Terminal-native software engineers, open-source contributors, and privacy-hyper-conscious enterprise developers. These are people running MLX, Ollama, or LM Studio bare-metal on Mac GPUs who actively despise the SaaS telemetry tax and vendor lock-in of tools like Cursor or GitHub Copilot.

### 5. Core Feature Set
*We are shipping exactly three features. Anything else is scope creep, and I will cut it.*

1.  **The "UNIX Pipe" Middleware:** Zero-config execution. `Siphon` natively bridges the file system to standard I/O. No daemons, no config files, no `.json` manifests. You point it at a directory, and it instantly translates the file tree into a standardized prompt structure compatible with any local runner. 
2.  **"Caveman" Token Compression:** Local models have strict, unforgiving context windows. `Siphon` uses an AST-aware engine to ruthlessly strip comments, minify whitespace, ignore `.gitignore` files, and collapse boilerplate logic. It forcefully packs the maximum amount of architectural signal into minimal tokens to prevent edge-model hallucination.
3.  **Universal LLM Socket:** It doesn't just format text; it knows how to talk to local runners out of the box. With native flags for standard local APIs, it bypasses the need for Python wrapper scripts. 

### 6. Technical Stack Recommendation
**Rust.** 
Do not even think about Node.js or Python for this. We need a zero-dependency, statically linked binary that executes in milliseconds. Rust guarantees the `ripgrep`/`bat` level of performance that UNIX power users expect. It screams "elite CLI" and is essentially a prerequisite for a command-line tool to trend at the top of Hacker News and GitHub today.

### 7. User Flow 
*Three steps. If they have to read a wiki to use it, we have failed.*

*   **Step 1: Install (Single Binary).**
    `curl -sS https://siphon.sh/install | bash` (Drops a single lightweight Rust binary directly into their PATH).
*   **Step 2: Target & Compress.**
    The user navigates to their messy project and defines their model's limit: `siphon ./src --max-tokens=8k`. The CLI instantly generates a minified, AST-optimized payload.
*   **Step 3: Pipe to Inference.**
    Chain it directly into their local runner of choice to create a frictionless, offline agent loop: 
    `siphon ./src | ollama run llama3 "Where is the race condition in this architecture?"`
