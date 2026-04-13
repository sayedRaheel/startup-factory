Listen up. The era of generic, bloated AI wrappers is dead. Developers don't want another chatbot; they want control. We are not building a monolithic enterprise platform that takes 6 months to onboard. We are building a surgical, ruthless micro-tool designed to instantly solve the exact pain point developers are crying about on Hacker News right now. 

Cut the bloat. Here is the strict Product Requirements Document.

### 1. Product Name
**Warden**

### 2. Goal Alignment Trace
I am proposing **Warden** (an ephemeral execution firewall for local agents) -> **because** the Scout identified that developers are bleeding time manually reverting hallucinated, broken code from reckless AI agents -> **because** our ultimate goal is to build a hyper-focused, viral developer tool that organically skyrockets to the #1 spot on GitHub Trending. 

### 3. One-Sentence Pitch
Warden is a lightweight CLI firewall that sandboxes autonomous coding agents, forcing them to independently pass your test suite before their code is allowed to touch your filesystem.

### 4. The Target Audience
Senior software engineers, indie hackers, and open-source maintainers who use local coding agents (like Goose, Cline, or Ollama) but are utterly exhausted by babysitting them and reverting botched, hallucinated commits. 

### 5. Core Feature Set (Strictly 3 Features)
We are building exactly three things. If a feature isn't on this list, it does not exist.

1. **Ephemeral Sandboxing (The Firewall):** 
   Warden intercepts all filesystem mutations attempted by the AI agent and instantly routes them to a hidden, temporary Git worktree. The agent thinks it's writing to your repo, but it’s actually contained in a secure sandbox. No overwriting critical logic. No corrupted states. 
2. **Auto-Verification Loop (The Interrogator):** 
   Once the agent finishes a task, Warden automatically triggers your project's local test suite (`npm test`, `cargo test`, etc.) against the sandbox. If it passes, Warden cleanly merges the diff. If it fails, Warden blocks the merge and aggressively pipes the `stderr` traceback back to the agent, forcing it to self-correct without user intervention.
3. **Persistent State Ledger (The Memory):** 
   A localized, lightweight `.warden` state file that tracks exactly what the agent attempted, the errors it hit, and the paths it took. This gives the agent localized "memory" across sessions, permanently preventing the dreaded infinite loop of trying the same broken solution twice. 

### 6. Technical Stack Recommendation
**Rust.**
Forget heavy Node.js runtimes or bloated Python environments. We are building a CLI utility that intercepts filesystem operations and manages sub-processes. Rust gives us bare-metal performance, memory safety, zero-dependency binaries, and massive hype appeal for the GitHub Trending page. We will use `clap` for the CLI interface and `git2` for the headless sandbox branching.

### 7. User Flow (3 Steps)
Installation: `cargo install warden-cli`

1. **Wrap:** The user prefixes their normal agent command with Warden: 
   `warden run goose "refactor the auth middleware"`
2. **Execute & Test:** Warden spawns the invisible sandbox, lets Goose write the code, and silently executes the test suite against the proposed changes.
3. **Merge or Bounce:** If the tests pass, Warden merges the code into the main working directory seamlessly. If they fail, Warden feeds the exact error back to Goose and says, *"Fix it."* The user sees nothing but the final, working result.
