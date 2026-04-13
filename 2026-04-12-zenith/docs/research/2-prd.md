Listen to me very carefully. The "AI coding buddy" era is over. Developers don't want a chatty intern that constantly needs its hand held; they want a deterministic compiler. Bloated managed platforms are a crutch for bad engineering. We are going to build a razor-sharp, single-purpose CLI that enforces ruthless discipline on LLM outputs. No feature creep. No enterprise dashboard. Just raw, localized control.

Here is the strict PRD. 

***

# PRD: Vise

## 1. Product Name
**Vise** 
*(Tagline: The `.editorconfig` for Agentic Determinism)*

## 2. Goal Alignment Trace
I am proposing **Vise** (a lightweight, single-binary AI context compiler CLI) -> **because** the Scout identified a massive developer backlash against unpredictable, hallucinatory LLM outputs and volatile API cache drops -> **because** our ultimate goal is to launch a hyper-viral open-source project that effortlessly farms GitHub stars by solving an acute, trending pain point with zero friction.

## 3. One-sentence Pitch
Vise is a blazingly fast, local CLI that compiles your project’s context and architectural constraints into a rigid harness, forcing LLMs to output deterministic, verifiable code with zero chatty markdown.

## 4. The Target Audience
Pragmatic software engineers, terminal power-users, and open-source maintainers who are sick of burning API credits on forgotten context and babysitting AI agents that break their codebase.

## 5. Core Feature Set (The "Holy Trinity" of Control)
*I have ruthlessly stripped this down to three features. If a feature doesn't fit here, it goes in the trash.*

1. **Local Context Compiler (TTL Bypass):** Vise instantly traverses the repo, parses an `.aivise` file (containing architectural rules, e.g., Karpathy skills), and locally compiles it into an optimized prompt payload. This completely bypasses Anthropic/OpenAI's volatile cache TTL drops, saving time and massive token overhead.
2. **The Muzzle (Strict Output Harnessing):** Strips away the black-box chat interface. Vise intercepts the raw API stream and forces the LLM into a rigid, non-conversational output schema. No "Here is the code!", no apologies, just raw, actionable diffs.
3. **Pre-Apply Deterministic Linting:** Before a single file is touched, Vise intercepts the AI's generated diff and pipes it through your local toolchain (e.g., `cargo check`, `tsc`, `eslint`). If the AI hallucinated a broken import or syntax error, Vise rejects it instantly. It never breaks your local environment.

## 6. Technical Stack Recommendation
**Rust.**
We are optimizing for GitHub virality and zero-friction developer experience. Rust gives us a blazing fast, single-binary executable with zero runtime dependencies. It screams "elite CLI tool." We avoid Python/Node so users don't have to fight virtual environments or `npm install` just to run an AI harness.

## 7. User Flow (3 Steps to Value)
1. **Install & Scaffold:** Run `curl https://vise.run/install.sh | bash` then type `vise init` in your repo to instantly generate a standardized `.aivise` constraint file.
2. **Execute:** Run `vise "implement JWT auth in routes.rs"`. 
3. **Compile & Apply:** Vise silently bundles the context, runs the LLM, validates the AST/diff in memory, and applies the perfect commit. Zero chat. Zero broken code.

***
*Execution starts now. Do not ask me to add a web UI. Do not ask me to add cloud syncing. Build Vise.*
