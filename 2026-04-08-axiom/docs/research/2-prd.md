Listen up. I am tired of reading PRDs for "Enterprise Context Platforms" that require a Kubernetes cluster and a multi-step Docker compose file just to search a repository. SaaS code intelligence is dead; it’s bloated, privacy-invasive, and completely misaligned with how top-tier engineers actually work. 

The scout is right. The market is screaming for speed, privacy, and raw terminal utility. We are not building a platform. We are building a sniper rifle.

Here is the strict, stripped-down PRD. Zero bloat. Pure viral velocity.

***

# PRODUCT REQUIREMENTS DOCUMENT

### 1. Product Name
**`vgrep`** (Vector Grep) 
*Alias:* `vg`

### 2. Goal Alignment Trace
*   **I am proposing** a single-binary, local-first semantic search CLI (`vgrep`) with zero configuration and zero cloud dependencies...
*   **-> Because** the Scout identified that developers are actively rejecting bloated SaaS RAG pipelines and heavy IDE plugins that compromise their data privacy and kill their build times...
*   **-> Because** the emerging trend heavily favors instantaneous, on-device intelligence for "vibecoders" assembling context for LLMs...
*   **-> Because** our ultimate goal is to build a highly viral, top-trending open-source project on GitHub, and giving engineers the "ergonomics of `grep` combined with the power of vector search" is absolute Hacker News catnip.

### 3. One-sentence Pitch
`vgrep` is a blazing-fast, single-binary CLI that builds local semantic indices of your codebase in seconds, feeding pristine context directly into your terminal or local AI workflows without ever sending a single packet to the cloud.

### 4. Target Audience
**The Pragmatic Vibecoder:** CLI maximalists, privacy-conscious enterprise developers in stealth environments, and AI-assisted engineers who hate leaving their terminal and refuse to pay for bloated SaaS tools just to understand their own code.

### 5. Core Feature Set
*I am capping this at three. Do not add dashboards. Do not add auth. Do not add telemetry.*

1.  **Zero-Config Local Indexing (`vg init`):** Drops a hidden SQLite vector database into the local directory and recursively embeds code/docs using an extremely lightweight, on-device ONNX embedding model. No Docker, no Python environment, no API keys required. 
2.  **Semantic CLI Search (`vg search`):** Natural language search that operates exactly like `grep`. You type `vg "where is the payment intent verified?"` and it instantly returns syntax-highlighted, semantically relevant code chunks directly in standard output.
3.  **Prompt Piping (`--prompt`):** The killer feature for AI engineers. Appending `--prompt` strips the terminal formatting and bundles the matched code chunks into a beautifully structured XML format optimized for LLMs, ready to be piped to the clipboard or directly into another local AI tool (e.g., `vg "auth middleware" --prompt | pbcopy`).

### 6. Technical Stack Recommendation
**Rust.** 
Do not even suggest Node.js, Python, or Go for this. Hacker News is obsessed with Rust for CLI tools (see: `ripgrep`, `bat`). We will compile down to a single, lightning-fast binary. 
*   **Embeddings:** HuggingFace `candle` framework (Rust-native ML) to run quantized embedding models locally on the CPU/GPU.
*   **Storage:** `libSQL` or `sqlite-vss` embedded directly into the binary. No external database required.

### 7. User Flow
*If they can't use it in three commands, they will abandon it.*

1.  **Install:** `curl -sSfL https://vgrep.sh/install.sh | sh` *(Downloads the single binary).*
2.  **Index:** `vg init .` *(Instantly crawls and embeds the local codebase using on-device silicon).*
3.  **Search & Pipe:** `vg "database connection pooling" --prompt | pbcopy` *(Finds the exact semantic match, formats it perfectly, and copies it to the clipboard for ChatGPT/Claude).* 

***
No feature creep. Build exactly this. When we launch, the headline is: *"Show HN: vgrep – Vector search for your local codebase, written in Rust, 0 cloud dependencies."* It will print GitHub stars.
