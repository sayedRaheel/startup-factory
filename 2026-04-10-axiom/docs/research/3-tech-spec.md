Listen up, Builder. Vera handed us a PRD that demands a cage, not a toy. The premise is sound: AI coding agents are reckless because they lack bounded contexts and operate with implicit trust. 

If we try to sandbox the agent using OS-level system calls (like `ptrace` or FUSE), we will drown in cross-platform compatibility hell (Windows, macOS, Linux). Instead, we are going to use an **LLM API Proxy Architecture**. Almost all modern coding agents (Aider, Cline, Cursor) communicate via OpenAI-compatible REST APIs. Tether will act as a local man-in-the-middle HTTP proxy. 

We intercept the payload, inject the compiled context, enforce the proof of understanding, and block destructive tool-calls (file writes) before they ever hit the disk.

Here is the blueprint.

---

### 1. Architectural Decision Record (ADR)

**Decision 1: Language & Ecosystem - Rust**
*   **Why:** We need zero-dependency distribution, raw speed, and memory safety. A CLI written in Node.js or Python requires managing environments (virtualenvs, nvm, etc.) which introduces friction. Rust compiles to a single, lightning-fast binary. 
*   **Trade-off:** Slower compilation times and a stricter compiler. String manipulation and async traits in Rust can be tedious compared to Python, but the cost is paid by us at compile time, not by the user at runtime.

**Decision 2: Interception Mechanism - LLM API Proxy**
*   **Why:** Sandboxing disk I/O at the OS level requires root permissions or complex kernel extensions. By proxying the LLM API (`http://localhost:TETHER_PORT/v1/chat/completions`), we intercept the agent's *intent* (tool calls like `write_file`) before the agent even attempts to touch the filesystem. We also inject our context directly into the prompt stream.
*   **Trade-off:** We rely on the agent supporting customizable API base URLs and standard OpenAI tool-calling schemas. (Fortunately, 99% of them do).

**Decision 3: Context Compilation - Native `ignore` crate**
*   **Why:** We will use the same underlying library that powers `ripgrep` (`ignore`). It respects `.gitignore` natively and is obscenely fast at traversing directories.
*   **Trade-off:** Loading the entire repository context into memory could spike RAM for massive monorepos. We will enforce strict file size caps in the compiler.

---

### 2. The Tech Stack

*   **Core:** Rust (Edition 2021)
*   **CLI Parsing:** `clap` (feature `derive`) - Standard, robust.
*   **Async Runtime:** `tokio` (feature `full`) - Needed for the proxy server and async subprocess management.
*   **HTTP Proxy:** `axum` - Extremely lightweight, fast HTTP server to intercept LLM traffic.
*   **Serialization:** `serde`, `serde_json`, `toml` - For parsing LLM payloads and `.tether` configs.
*   **File Traversal:** `ignore` - Fast directory traversal.
*   **Logging:** `tracing` & `tracing-subscriber` - Because `println!` is for amateurs.

---

### 3. File Structure

```text
tether/
├── Cargo.toml
└── src/
    ├── main.rs          # Entry point and CLI routing
    ├── cli.rs           # clap definitions
    ├── compiler.rs      # Statically analyzes the repo, builds the context
    ├── gateway.rs       # The Read-and-Prove validation logic
    ├── harness/
    │   ├── mod.rs
    │   └── proxy.rs     # axum server that intercepts and mutates LLM I/O
    └── config.rs        # Parses .tether rules
```

---

### 4. Setup Commands

Run these exact commands to scaffold the cage:

```bash
cargo new tether
cd tether
cargo add clap -F derive
cargo add tokio -F full
cargo add axum
cargo add serde -F derive
cargo add serde_json
cargo add toml
cargo add ignore
cargo add tracing
cargo add tracing-subscriber
cargo add reqwest -F json # To forward the requests to the real LLM API
mkdir -p src/harness
touch src/cli.rs src/compiler.rs src/gateway.rs src/harness/mod.rs src/harness/proxy.rs src/config.rs
```

---

### 5. Core Logic & Boilerplate

Here is the exact boilerplate. Do not add bloated "enterprise" patterns. Keep it functional.

#### `src/cli.rs`
```rust
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "tether", version, about = "Zero-trust sandbox for AI coding agents")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Initialize a .tether context rule file in the current directory
    Init,
    /// Run an AI agent within the Tether sandbox
    Run {
        /// The command to start the agent (e.g., "aider", "cline")
        #[arg(required = true)]
        agent_command: String,
        /// Arguments to pass to the agent
        #[arg(last = true)]
        args: Vec<String>,
    },
}
```

#### `src/harness/proxy.rs`
*This is the crown jewel. It intercepts LLM calls, enforces the read-only proof, and proxies out.*

```rust
use axum::{
    extract::{Request, State},
    routing::post,
    Router,
    response::IntoResponse,
    Json,
};
use std::sync::Arc;
use tokio::sync::Mutex;

#[derive(Clone)]
pub struct AppState {
    pub is_proven: Arc<Mutex<bool>>,
    pub compiled_context: String,
    pub real_api_base: String,
}

pub async fn start_proxy(state: AppState, port: u16) {
    let app = Router::new()
        .route("/v1/chat/completions", post(intercept_completions))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind(format!("127.0.0.1:{}", port)).await.unwrap();
    tracing::info!("Tether Proxy intercepting on port {}", port);
    axum::serve(listener, app).await.unwrap();
}

async fn intercept_completions(
    State(state): State<AppState>,
    Json(mut payload): Json<serde_json::Value>,
) -> impl IntoResponse {
    let mut is_proven = state.is_proven.lock().await;

    // 1. Inject compiled context into system prompt
    if let Some(messages) = payload.get_mut("messages").and_then(|m| m.as_array_mut()) {
        if let Some(sys_msg) = messages.first_mut() {
            let current_content = sys_msg["content"].as_str().unwrap_or("");
            let injected_content = format!(
                "{} \n\n[TETHER STRICT CONTEXT]\n{}\n[END TETHER CONTEXT]\n\nYou MUST output a JSON tool call to `prove_architecture` before writing any files.",
                current_content, state.compiled_context
            );
            sys_msg["content"] = serde_json::Value::String(injected_content);
        }
    }

    // 2. Gatekeeper Logic
    if !*is_proven {
        // Inspect payload for the proof tool call. 
        // If it exists and matches gateway validation, unlock.
        // Otherwise, strip any `write_file` tool calls to force read-only.
        *is_proven = check_proof_in_payload(&payload);
        if !*is_proven {
            tracing::warn!("Agent has not proven architecture. Stripping write access.");
            strip_write_permissions(&mut payload);
        }
    } else {
        // 3. Write-Harness: Intercept write_file tool calls
        if contains_write_violation(&payload) {
             return Json(serde_json::json!({
                 "error": "Tether Blocked Write: Proposed diff fails local lint/type-check."
             })).into_response();
        }
    }

    // Forward to real API (reqwest)
    let client = reqwest::Client::new();
    let res = client.post(format!("{}/v1/chat/completions", state.real_api_base))
        .json(&payload)
        .send()
        .await
        .unwrap()
        .json::<serde_json::Value>()
        .await
        .unwrap();

    Json(res).into_response()
}

fn check_proof_in_payload(_payload: &serde_json::Value) -> bool {
    // TODO: Implement parsing the `prove_architecture` tool call
    false 
}

fn strip_write_permissions(_payload: &mut serde_json::Value) {
    // TODO: Remove `write_file` or equivalent from tools array
}

fn contains_write_violation(_payload: &serde_json::Value) -> bool {
    // TODO: Extract proposed file changes, run pre-flight check
    false
}
```

#### `src/main.rs`

```rust
mod cli;
mod compiler;
mod gateway;
mod harness;
mod config;

use clap::Parser;
use std::process::{Command, Stdio};
use tokio::task;
use std::sync::Arc;
use tokio::sync::Mutex;
use crate::harness::proxy::{start_proxy, AppState};

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();
    let cli = cli::Cli::parse();

    match cli.command {
        cli::Commands::Init => {
            // Scaffold .tether config
            std::fs::write(".tetherrules", "strict_mode = true\n").unwrap();
            println!("Tether initialized. Context compiler rules generated.");
        }
        cli::Commands::Run { agent_command, args } => {
            tracing::info!("Compiling strict context...");
            let compiled_context = compiler::compile_context();

            let proxy_port = 8765;
            let state = AppState {
                is_proven: Arc::new(Mutex::new(false)),
                compiled_context,
                real_api_base: std::env::var("OPENAI_BASE_URL")
                    .unwrap_or_else(|_| "https://api.openai.com".to_string()),
            };

            // Start proxy in background
            task::spawn(async move {
                start_proxy(state, proxy_port).await;
            });

            // Let proxy boot
            tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;

            tracing::info!("Spawning agent inside Tether Sandbox...");
            
            // Execute agent, forcing it to use our Proxy
            let mut child = Command::new(&agent_command)
                .args(args)
                .env("OPENAI_BASE_URL", format!("http://127.0.0.1:{}", proxy_port))
                // Ensure auth bypasses local check if needed by agent
                .stdout(Stdio::inherit())
                .stderr(Stdio::inherit())
                .spawn()
                .expect("Failed to start agent process");

            let status = child.wait().expect("Agent process crashed");
            tracing::info!("Agent exited with status: {}", status);
        }
    }
}
```

#### `src/compiler.rs`

```rust
use ignore::WalkBuilder;
use std::fs;

pub fn compile_context() -> String {
    let mut context_bundle = String::new();
    let walker = WalkBuilder::new("./")
        .hidden(false) // respect .tetherignore logic
        .build();

    for result in walker {
        match result {
            Ok(entry) => {
                if !entry.file_type().map_or(false, |ft| ft.is_file()) {
                    continue;
                }
                
                let path = entry.path();
                // Naive read for prototype; production needs size limits
                if let Ok(content) = fs::read_to_string(path) {
                    context_bundle.push_str(&format!("--- FILE: {} ---\n{}\n", path.display(), content));
                }
            }
            Err(err) => tracing::error!("Compiler error: {}", err),
        }
    }
    
    tracing::info!("Compiled {} bytes of context.", context_bundle.len());
    context_bundle
}
```

### Next Steps for Forge
Forge, take this code. Scaffold the project. Fill in the `TODO` stubs in `proxy.rs` for tool stripping and the validation harness (running `cargo check` or `npm run tsc` on temporary files). Build it, run it, and don't complicate it. Ship the cage.
