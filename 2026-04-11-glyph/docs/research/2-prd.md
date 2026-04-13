**1. Product Name**
**Grip** (CLI: `grip`)

**2. Goal Alignment Trace**
I am proposing **Grip (a dynamic context routing CLI)** -> *because* the Scout identified that **engineers are bleeding hours babysitting hallucinatory AI relying on brittle, 2,000-line static `CLAUDE.md` files** -> *because* our ultimate goal is to **build a viral, zero-friction open-source tool that organically dominates GitHub trending by instantly eliminating developer pain.** 

**3. One-sentence Pitch**
Grip is a blazing-fast, local CLI that replaces bloated repository-wide AI instructions with dynamic, path-aware context routing, forcing your AI to write deterministic code without changing your workflow.

**4. The Target Audience**
Senior engineers, tech leads, and heavy Cursor/Copilot CLI users who are absolutely sick of reviewing hallucinated garbage code and refuse to adopt bloated, proprietary agent-orchestration platforms just to enforce basic architectural boundaries. 

**5. Core Feature Set (Strictly 3. No Feature Creep.)**
*   **Feature 1: Git-Aware Dynamic Context Compilation.** 
    No more monolithic `CLAUDE.md`. Grip uses localized `.grip.toml` files scattered throughout your repo. When you run a command, Grip intelligently compiles a single, hyper-targeted context string based *only* on your current working directory, staged files, and active `git branch`. If the AI is touching the database layer, it only gets the database rules.
*   **Feature 2: Standardized Pre-Flight Injection Hook.** 
    Zero lock-in. Grip doesn't execute the AI; it controls its brain. Exposes a simple `grip prompt` command that instantly pipes the perfectly scoped context directly into Cursor, Copilot, or your terminal-based LLM. 
*   **Feature 3: Post-Generation Determinism Linter.** 
    Trust nothing. `grip validate` acts as a hyper-fast post-flight checklist. It parses the AI's diff against the local directory's active rules (e.g., "Must use React Router v6", "Never import lodash") and instantly flags violations before the garbage code ever gets staged.

**6. Technical Stack Recommendation**
*   **Language:** **Rust**. Period. 
*   **Why:** It screams modern performance, ships as a single zero-dependency binary, and Rust CLI tools intrinsically trend well on GitHub (e.g., `ripgrep`, `bat`). We use TOML for configuration because it is lightweight, standard, and readable. We actively reject Python or Node.js for this to avoid versioning hell and runtime bloat.

**7. User Flow (3 Steps. Instant Value.)**
1.  **Install & Init:** Run `brew install grip` (or curl script). Run `grip init` to auto-split their existing bloated `CLAUDE.md` into highly scoped `src/ui/.grip.toml` and `src/db/.grip.toml` files.
2.  **Act:** Developer works normally. When asking the AI to build a feature, they simply use `` `grip pipe` `` to feed perfectly scoped rules directly into their AI tool of choice based on what files they are currently touching.
3.  **Validate:** After the AI writes the code, the developer runs `grip validate` to automatically verify the AI didn't hallucinate dependencies or break the local architectural boundaries before committing. 

*We build these three things perfectly. Nothing else. Execute.*
