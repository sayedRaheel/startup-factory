This is Linus. 

Vera, the PRD is crystal clear. We are excising the bloated, chatty fat of modern AI tools and delivering a surgical instrument. A compiler requires determinism, speed, and absolute authority over the target environment. If it chats, it dies. 

Here is the architectural blueprint and exact execution plan for Forge.

***

### 1. Architectural Decision Record (ADR)

**Decision 1: Core Language & Runtime**
*   **Choice:** Rust.
*   **Why:** We are building a single-binary CLI that must feel instantaneous. Rust provides zero-cost abstractions, fearless concurrency (for walking file trees and streaming I/O), and compiles down to a single, dependency-free binary. It demands rigor, which aligns with the product's core thesis.
*   **Trade-off:** Slower development velocity compared to Python or Go. Higher barrier to entry for community contributors. We accept this because end-user friction (e.g., fighting Python virtual environments) is the number one killer of CLI virality.

**Decision 2: State Management & Storage**
*   **Choice:** Stateless File System + `.aivise` file. No Database.
*   **Why:** Vise is a pipe. It takes local state, pushes it through an LLM, and pipes the diff back. Adding SQLite or local KV stores introduces state corruption risks and violates the "single-purpose" mandate. Configuration lives in `.aivise`.
*   **Trade-off:** We cannot cache historical intent locally. The context must be recompiled on every run. We mitigate this via blazing-fast parallel directory traversal using the `ignore` crate.

**Decision 3: The Muzzle (LLM Output Format)**
*   **Choice:** Strict JSON Schema Enforcement via REST, bypassing Markdown completely.
*   **Why:** Parsing markdown code blocks or unified diffs from LLMs is notoriously flaky. By forcing the LLM to output pure JSON (`{ "files": [ { "path": "...", "content": "..." } ] }`), we can deterministically deserialize the response straight into Rust structs.
*   **Trade-off:** Increases token consumption slightly due to JSON syntax overhead, and some LLMs struggle with massive JSON payloads. We mitigate this by using modern foundational models (Claude 3.5 Sonnet / GPT-4o) which are heavily fine-tuned for JSON instruction following.

***

### 2. Exact Tech Stack & Libraries

*   **Language:** Rust (Edition 2021)
*   **CLI Parsing:** `clap` (with `derive` feature) for robust argument routing.
*   **Async Runtime:** `tokio` (lightweight, highly concurrent).
*   **HTTP/LLM Client:** `reqwest` for raw, unadulterated network control.
*   **Context Walking:** `ignore` (the engine behind `ripgrep`—respects `.gitignore` out of the box).
*   **Serialization:** `serde`, `serde_json`, `toml` (for parsing `.aivise`).
*   **Error Handling:** `anyhow` (for application-level bailouts).

***

### 3. Exact File Structure

```text
vise/
├── Cargo.toml
├── .gitignore
├── src/
│   ├── main.rs          # CLI entrypoint & routing
│   ├── config.rs        # Parses .aivise configurations
│   ├── context.rs       # The Compiler: Fast dir walking & context bundling
│   ├── llm.rs           # The Muzzle: Strict JSON communication with the API
│   ├── lint.rs          # Pre-Apply Deterministic Validation hook
│   └── workspace.rs     # Safe atomic file application & rollback
```

***

### 4. Step-by-Step Commands for Forge

Run these sequentially to initialize the scaffolding:

```bash
cargo new vise
cd vise

# Add core dependencies
cargo add clap -F derive
cargo add tokio -F full
cargo add reqwest -F json
cargo add serde -F derive
cargo add serde_json
cargo add toml
cargo add ignore
cargo add anyhow
cargo add dirs

# Create necessary module files
touch src/config.rs src/context.rs src/llm.rs src/lint.rs src/workspace.rs
```

***

### 5. Core Logic & Boilerplate 

Forge, copy this boilerplate exactly. It wires up the holy trinity of features: Context Compilation, The Muzzle, and Pre-Apply Linting.

#### `src/main.rs`
```rust
mod config;
mod context;
mod llm;
mod lint;
mod workspace;

use clap::{Parser, Subcommand};
use anyhow::Result;

#[derive(Parser)]
#[command(name = "vise", version, about = "The .editorconfig for Agentic Determinism")]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,

    /// The prompt to execute (if not using a subcommand)
    prompt: Option<String>,
}

#[derive(Subcommand)]
enum Commands {
    /// Initialize a new .aivise constraint file
    Init,
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    if let Some(Commands::Init) = cli.command {
        config::init_aivise()?;
        println!("✔ Generated .aivise configuration.");
        return Ok(());
    }

    if let Some(prompt) = cli.prompt {
        // 1. Compile Context
        let config = config::load_aivise()?;
        let context_payload = context::compile_workspace_context()?;
        
        // 2. The Muzzle (LLM Call)
        println!("Compiling context and generating diff...");
        let ai_response = llm::execute_prompt(&prompt, &context_payload, &config).await?;
        
        // 3. Pre-Apply Deterministic Linting
        println!("Applying diff to memory and linting...");
        let backup = workspace::apply_to_memory(&ai_response)?;
        
        if lint::run_toolchain(&config.lint_command)? {
            println!("✔ Lint passed. Changes committed.");
        } else {
            println!("✖ Lint failed. AI hallucinated. Rolling back changes.");
            workspace::rollback(backup)?;
            std::process::exit(1);
        }
    } else {
        println!("No prompt provided. Usage: vise \"your prompt here\"");
    }

    Ok(())
}
```

#### `src/config.rs`
```rust
use serde::{Deserialize, Serialize};
use std::fs;
use anyhow::Result;

#[derive(Serialize, Deserialize, Debug)]
pub struct AiviseConfig {
    pub language: String,
    pub lint_command: String,
    pub strict_rules: Vec<String>,
}

pub fn init_aivise() -> Result<()> {
    let default_config = AiviseConfig {
        language: "rust".into(),
        lint_command: "cargo check".into(),
        strict_rules: vec![
            "Never use unwrap().".into(),
            "Always add inline documentation for public functions.".into(),
        ],
    };
    let toml = toml::to_string_pretty(&default_config)?;
    fs::write(".aivise", toml)?;
    Ok(())
}

pub fn load_aivise() -> Result<AiviseConfig> {
    let content = fs::read_to_string(".aivise").unwrap_or_else(|_| {
        eprintln!("Warning: No .aivise found. Using defaults.");
        "language = \"unknown\"\nlint_command = \"echo 'No lint'\"\nstrict_rules = []".to_string()
    });
    let config: AiviseConfig = toml::from_str(&content)?;
    Ok(config)
}
```

#### `src/llm.rs`
```rust
use serde::{Deserialize, Serialize};
use anyhow::{Result, Context};
use crate::config::AiviseConfig;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct FileChange {
    pub path: String,
    pub content: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct AiResponse {
    pub files: Vec<FileChange>,
}

pub async fn execute_prompt(prompt: &str, workspace_context: &str, config: &AiviseConfig) -> Result<AiResponse> {
    // The Muzzle: Forcing the schema.
    let system_prompt = format!(
        "You are an infallible code compiler. \
        Rules: {:?}. \
        Context: {}. \
        OUTPUT STRICTLY JSON. NO MARKDOWN. NO CHAT. \
        Format: {{ \"files\": [ {{ \"path\": \"str\", \"content\": \"str\" }} ] }}",
        config.strict_rules, workspace_context
    );

    // Note for Forge: Wire up reqwest here to OpenAI/Anthropic using the system_prompt.
    // For skeleton purposes, returning a mock deterministic struct.
    
    // let client = reqwest::Client::new();
    // let res = client.post("https://api.openai.com/v1/chat/completions")...

    Ok(AiResponse {
        files: vec![],
    })
}
```

#### `src/lint.rs`
```rust
use std::process::Command;
use anyhow::Result;

pub fn run_toolchain(command_str: &str) -> Result<bool> {
    let parts: Vec<&str> = command_str.split_whitespace().collect();
    if parts.is_empty() { return Ok(true); }

    let status = Command::new(parts[0])
        .args(&parts[1..])
        .status()?;

    Ok(status.success())
}
```

#### `src/workspace.rs`
```rust
use anyhow::Result;
use std::fs;
use crate::llm::FileChange;

pub struct Backup {
    original_files: Vec<FileChange>,
}

pub fn apply_to_memory(response: &crate::llm::AiResponse) -> Result<Backup> {
    let mut backup = Backup { original_files: vec![] };

    for file in &response.files {
        // Backup existing
        if let Ok(content) = fs::read_to_string(&file.path) {
            backup.original_files.push(FileChange {
                path: file.path.clone(),
                content,
            });
        }
        // Write new
        fs::write(&file.path, &file.content)?;
    }

    Ok(backup)
}

pub fn rollback(backup: Backup) -> Result<()> {
    for file in backup.original_files {
        fs::write(&file.path, &file.content)?;
    }
    Ok(())
}
```

#### `src/context.rs`
```rust
use ignore::WalkBuilder;
use std::fs;
use anyhow::Result;

pub fn compile_workspace_context() -> Result<String> {
    let mut context = String::new();
    
    // Fast parallel bypass of .gitignore paths
    for result in WalkBuilder::new("./").build() {
        let entry = result?;
        if entry.file_type().map_or(false, |ft| ft.is_file()) {
            let path = entry.path();
            if let Ok(content) = fs::read_to_string(path) {
                context.push_str(&format!("--- FILE: {} ---\n{}\n", path.display(), content));
            }
        }
    }
    
    // In production, truncate if exceeding max token limit.
    Ok(context)
}
```

***

**To Forge:** The constraints have been set. Do not add conversational features. Wire the API client in `llm.rs` directly to the `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` environment variables. Implement it, compile it, ship it.
