# Product Requirements Document (PRD)

**1. Product Name**
**AgentBox**

**2. Goal Alignment Trace**
I am proposing **AgentBox** (a zero-config sandbox and credential vault for local AI) -> **because** the Scout identified that developers are terrified of local AI agents executing destructive commands and leaking credentials due to unchecked system access -> **because** our ultimate goal is to build viral, high-impact open-source tools that farm GitHub stars by solving immediate, bleeding-edge developer anxieties.

**3. One-sentence Pitch**
AgentBox is an ultra-lightweight CLI that wraps your local AI agents in a strict execution sandbox, securely injecting context while locking down credentials and preventing out-of-bounds file system modifications.

**4. The Target Audience**
"Vibecoders" and engineers running local, autonomous AI agents (like Claude Code, AutoGPT, or custom swarm engines) who are terrified of their agent accidentally logging their AWS keys, running `rm -rf`, or exfiltrating sensitive system files. 

**5. Core Feature Set**
*Forget bloated vector databases and enterprise RAG. We are building exactly three things, and they will work flawlessly:*
1. **Air-gapped Credential Injection:** Secrets are dynamically provided to the agent's runtime environment for use, but strictly masked from being read, printed, logged, or exfiltrated by the agent itself. 
2. **Strict Execution Sandboxing:** AgentBox intercepts all shell commands and filesystem writes. Anything outside the designated project "safe zone" requires explicit developer `y/N` approval or matches a strict `.agentbox` allowlist.
3. **Curated Context Scoping:** Forces the agent to operate exclusively within a curated memory boundary, passing only approved local files into context and preventing it from blindly indexing irrelevant or sensitive global directories.

**6. Technical Stack Recommendation**
* **Language:** **Rust**. We need system-level process isolation, blazing-fast startup times, and memory safety. It also trends wildly on GitHub for CLI tools. (Use `clap` for the CLI and `tokio` for async process interception).
* *No heavy databases, no Python bloat. Single, fast binary.*

**7. User Flow**
*Keep it under 30 seconds to "Aha!" moment.*
1. **Install:** `curl -sL agentbox.dev/install.sh | bash` (or `cargo install agentbox`).
2. **Scope:** Run `agentbox init` in your project root to instantly generate an `.agentbox.yml` defining your safe directory and environment variables.
3. **Run:** Execute your agent via the vault (e.g., `agentbox run claude-code`). The agent works seamlessly but is violently halted the millisecond it tries to touch a file or execute a command outside its sandbox.
