Listen up. The "AI writes my code" honeymoon isn't just dead; it's rotting. Developers are drowning in AI-generated technical debt because we handed a loaded gun to a toddler. They don’t want smarter models; they want control. They want boundaries. 

We are not building a platform. We are not building an enterprise suite. We are building a cage.

Here is the strict, ruthlessly scoped PRD. Nothing more, nothing less. 

***

# PRODUCT REQUIREMENTS DOCUMENT

### 1. Product Name
**Tether**

### 2. Goal Alignment Trace
**I am proposing** a strict, zero-trust context compiler and sandbox CLI -> **because the Scout identified** that developers are bleeding hours rolling back AI-generated regressions caused by agents ignoring local architecture -> **because our ultimate goal is** to build a viral, high-utility project that rockets to the top of GitHub trending by solving acute, excruciating developer friction.

### 3. One-Sentence Pitch
Tether is a lightning-fast CLI that locks autonomous AI coding agents into a strict, deterministic sandbox, forcing them to mathematically prove they understand your local architecture before they are granted write access.

### 4. Target Audience
Pragmatic software engineers, open-source maintainers, and tech leads who rely on local AI coding assistants (like Aider, Cursor, or Cline) but are exhausted by babysitting non-deterministic output and reverting hallucinated codebase regressions.

### 5. Core Feature Set (Maximum 3)
*Cut the bloat. If it doesn't enforce predictability, it doesn't ship.*

1. **The Context Compiler (`.tetherignore` & Rule Compilation):** 
   Replaces fragile `CLAUDE.md` files. Tether statically analyzes the repository and aggressively strips out irrelevant files, compiling a dense, mathematically bounded context payload. If your architectural rules are contradictory, Tether fails the build before the AI even boots up.
2. **The "Read-and-Prove" Gateway:** 
   Zero-trust architecture for agents. Tether intercepts the agent's initialization and forces it into a read-only environment. The agent *must* output an architectural proof-of-understanding (a dependency map or logic tree) that matches Tether’s static analysis before write permissions to the disk are unlocked.
3. **The Deterministic Write-Harness:** 
   Once unlocked, Tether intercepts every file operation the AI attempts. It acts as an absolute gatekeeper, running the proposed diff through a pre-flight local linter and type-checker. If the agent introduces a syntax error, type violation, or touches a restricted directory, the write is blocked and the agent is forcefully restarted.

### 6. Technical Stack Recommendation
**Rust.** 
*Why:* It screams "memory-safe, fast, and strict." The GitHub hype cycle eats up Rust-based CLIs replacing legacy tooling (see: `ripgrep`, `uv`, `turbopack`). It compiles to a single, lightning-fast binary with zero dependencies. We use `clap` for the CLI interface and `tokio` for async interceptors of agent I/O streams. No bloated Node.js environments. No Python dependency hell. Just raw, native speed.

### 7. User Flow 
*Three steps. No onboarding tutorials. Just execution.*

1. **Initialize:** Developer drops the binary and runs `tether init`. Tether instantly maps the repo boundaries and generates a strict `.tether rules` file. 
2. **Bind & Prove:** Developer runs `tether run [agent-command]` (e.g., `tether run aider`). Tether hijacks the execution, feeds the strict compiled context to the agent, and demands a read-only architectural proof. 
3. **Execute:** Once the agent passes the gateway, it begins coding. Tether sits invisibly in the background, intercepting and blocking any file writes that violate the local conventions, ensuring a pristine commit. 

*** 

Ship this. Cut everything else. Let the viral traction do the talking.
