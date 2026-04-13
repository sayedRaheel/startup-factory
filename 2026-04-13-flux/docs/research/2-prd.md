Listen closely. The era of bloated, "kitchen-sink" AI wrappers is dead. Developers are bleeding cash and compute time because their tools are stupid, amnesiac, and wasteful. We are not building another AI agent; we are building the infrastructure that stops AI agents from bankrupting their users. 

Here is the finalized PRD. No scope creep. No nice-to-haves. Just three features designed to hit the top of Hacker News and dominate the GitHub trending page by tomorrow.

***

# PRODUCT REQUIREMENTS DOCUMENT (PRD)

### 1. Product Name
**TokenWall**

### 2. Goal Alignment Trace
I am proposing **TokenWall (a local caching API proxy)** -> because the Scout identified that **developers are exhausting their daily LLM API quotas in hours due to amnesiac, stateless agent loops re-reading the exact same boilerplate** -> because our ultimate goal is to **build a viral, high-utility open-source project that garners massive GitHub stars** by instantly stopping the most acute financial and technical pain point in the AI engineering space today.

### 3. One-Sentence Pitch
TokenWall is a blazing-fast local proxy that sits between your terminal and the LLM API to aggressively cache filesystem context, compress chat memory locally, and firewall runaway AI agents before they burn your API quota.

### 4. The Target Audience
CLI-native power developers, AI engineers, and open-source contributors running autonomous agent loops (e.g., Claude Code, Aider, OpenDevin) who are furious about hitting rate limits and paying for duplicate token processing by 11:00 AM. 

### 5. Core Feature Set (The "Holy Trinity" - Maximum 3)
*If it's not on this list, we aren't building it.*

1. **Semantic Filesystem Caching (The Token Saver):** TokenWall intercepts the outgoing JSON payload from the AI agent. Instead of blindly forwarding the 200,000-token project context, it diffs the local file tree. Unchanged files are stripped and replaced with cached vector embeddings/summaries, drastically cutting outgoing token volume.
2. **The "Rogue Loop" Firewall (The Wallet Saver):** A hard, deterministic kill-switch. Users set strict budgets (`--max-spend 5.00/day` or `--max-tokens 100k/hr`). If a headless agent gets stuck in a hallucination loop and tries to exceed the limit, TokenWall immediately severs the connection and kills the process. 
3. **Local Memory Compression (The Context Saver):** Offloads conversational history summarization to a cheap, local LLM (like Ollama running Llama 3 or Gemma 2) before passing the distilled prompt to the expensive Anthropic/OpenAI endpoint.

### 6. Technical Stack Recommendation
**Rust (Tokio + Axum)**
*Rationale:* We are building a proxy. It needs to be blazingly fast with zero latency overhead. Rust guarantees memory safety, compiles to a single, easily distributable binary, and completely avoids the bloat of Node.js or Python environments. Rust projects naturally attract high-tier GitHub stars and signal extreme performance to the Hacker News crowd. No enterprise garbage; just a raw, fast executable.

### 7. User Flow (3 Steps to Value)
We respect the user's time. Zero configuration required to start saving money.

1. **Install:** `curl -sL https://tokenwall.dev/install.sh | bash`
2. **Ignite:** `tokenwall start --budget $5/day` (Spins up the proxy on `localhost:8080`).
3. **Route:** Run your agent with the environment variable pointed at the wall: `ANTHROPIC_BASE_URL="http://localhost:8080" claude-code`

***
**Execution Mandate:** Do not add a GUI. Do not add cloud syncing. Build the binary, write a stellar `README.md` with a chart showing token savings, and ship it.
