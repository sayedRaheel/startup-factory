I am Linus. Vera’s PRD is brutal, focused, and exactly what the market demands right now. Kitchen-sink wrappers are dead. Developers want surgical tools that respect their time, their compute, and their wallets. 

Every decision in a proxy architecture has a trade-off. We are sitting on the critical path between the developer's agent and the LLM. If we add 500ms of latency, the tool feels sluggish and they will uninstall it. If we parse streaming responses incorrectly, the agent’s loop breaks.

Here is the Architectural Decision Record and the blueprint for Forge to build **TokenWall**.

***

### 1. Architectural Decision Record (ADR)

**Context:** We need a local API proxy to intercept, modify, cache, and firewall JSON payloads destined for OpenAI/Anthropic endpoints. It must run locally on developer machines with zero configuration.
**Decision:** We will build this in **Rust** using **Axum** (Web Framework), **Tokio** (Async Runtime), and **Rusqlite** (Embedded DB).
**Trade-offs:**
*   **Performance vs. Iteration Speed:** Rust guarantees predictable tail latencies (no garbage collection pauses interrupting SSE streams) and compiles to a highly distributable single binary. *Trade-off:* Go would have been 30% faster to write, but Rust captures the "blazing fast" Hacker News mindshare and ensures absolute memory safety for parsing arbitrary API payloads.
*   **State Management:** We chose an embedded SQLite database (`rusqlite`) over a pure key-value store or flat files. *Trade-off:* It adds a C-dependency (bundled) to the compilation step, but gives us transactional guarantees for tracking the `$5/day` budget and querying historical spend by hour, which is critical for the Firewall feature.
*   **Interception (Streaming):** We must intercept HTTP requests, mutate the JSON body (cache diffing, compression), and forward it. *Trade-off:* Mutating requests is easy. Parsing the returning Server-Sent Events (SSE) stream to calculate *actual* token usage before updating the firewall DB is complex and requires specialized stream-handling in Axum.

---

### 2. Exact Tech Stack & Libraries

*   **Language:** Rust (Edition 2021)
*   **Async Runtime:** `tokio` (Features: `full`) - Industry standard, bulletproof.
*   **HTTP Server:** `axum` - Ergonimic, fast, works seamlessly with Tokio.
*   **HTTP Client:** `reqwest` (Features: `json`, `stream`) - For forwarding requests to Anthropic/OpenAI and Ollama.
*   **CLI Parsing:** `clap` (Features: `derive`) - Standard for robust CLIs.
*   **Database:** `rusqlite` (Features: `bundled`) - Local budget and hash state.
*   **Serialization:** `serde`, `serde_json` - For intercepting and rewriting LLM payloads.
*   **Hashing:** `sha2` - For rapid file diffing to enable Semantic Caching.
*   **Token Estimation:** `tiktoken-rs` - For fast, local token counting without hitting APIs.

---

### 3. File Structure

```text
tokenwall/
├── Cargo.toml
├── src/
│   ├── main.rs       # CLI entry point, Clap config, Tokio setup
│   ├── server.rs     # Axum router and state injection
│   ├── proxy.rs      # Core request interception and forwarding logic
│   ├── firewall.rs   # Budget tracking, kill-switch logic (SQLite)
│   ├── cache.rs      # File hashing and semantic diffing
│   ├── compress.rs   # Ollama integration for local memory distillation
│   ├── models.rs     # Serde structs for LLM API payloads
│   └── db.rs         # SQLite initialization and schema setup
```

---

### 4. Step-by-Step Setup Commands

Forge, run these exact commands to scaffold the environment. No deviations.

```bash
# 1. Initialize the project
cargo new tokenwall
cd tokenwall

# 2. Add dependencies
cargo add tokio -F full
cargo add axum
cargo add reqwest -F json,stream
cargo add clap -F derive
cargo add serde -F derive
cargo add serde_json
cargo add rusqlite -F bundled
cargo add sha2
cargo add tiktoken-rs
cargo add tracing tracing-subscriber
cargo add anyhow

# 3. Scaffold the exact file structure
touch src/server.rs src/proxy.rs src/firewall.rs src/cache.rs src/compress.rs src/models.rs src/db.rs
```

---

### 5. Core Logic & Boilerplate Code

Forge, here is the architectural scaffolding. The wiring is strict to ensure state is shared safely across concurrent async threads.

#### `src/main.rs`
The entry point. Sets up tracing, parses CLI args, initializes the DB, and starts the server.
```rust
use clap::Parser;
use tracing::{info, Level};
use std::sync::Arc;

mod server;
mod proxy;
mod firewall;
mod cache;
mod compress;
mod models;
mod db;

#[derive(Parser, Debug)]
#[command(name = "TokenWall", version, about = "Local caching API proxy for LLMs")]
struct Args {
    #[arg(short, long, default_value_t = 8080)]
    port: u16,

    /// Daily budget in USD (e.g., 5.00)
    #[arg(short, long, default_value_t = 5.0)]
    budget: f64,
}

#[derive(Clone)]
pub struct AppState {
    pub db_pool: Arc<std::sync::Mutex<rusqlite::Connection>>,
    pub http_client: reqwest::Client,
    pub daily_budget: f64,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt().with_max_level(Level::INFO).init();
    let args = Args::parse();

    info!("Initializing TokenWall Firewall...");
    let db_conn = db::init_db()?;
    
    let state = AppState {
        db_pool: Arc::new(std::sync::Mutex::new(db_conn)),
        http_client: reqwest::Client::new(),
        daily_budget: args.budget,
    };

    info!("TokenWall ignited. Routing on localhost:{} with budget ${}/day", args.port, args.budget);
    server::start(args.port, state).await?;

    Ok(())
}
```

#### `src/server.rs`
Axum routing. We use a catch-all route to act as a true reverse proxy.
```rust
use axum::{
    routing::{post, get},
    Router,
    extract::State,
};
use std::net::SocketAddr;
use crate::AppState;
use crate::proxy::handle_proxy_request;

pub async fn start(port: u16, state: AppState) -> anyhow::Result<()> {
    let app = Router::new()
        // Catch-all for API endpoints (e.g., /v1/chat/completions)
        .route("/*path", post(handle_proxy_request))
        .with_state(state);

    let addr = SocketAddr::from(([127, 0, 0, 1], port));
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;
    
    Ok(())
}
```

#### `src/proxy.rs`
The heart of the system. This implements the 3 features: Firewall check, Cache extraction, Compression, and Forwarding.
```rust
use axum::{
    extract::{State, Path},
    http::{Request, StatusCode, HeaderMap},
    body::Body,
    response::IntoResponse,
};
use axum::response::Response;
use crate::AppState;
use crate::firewall;
use crate::cache;
use crate::compress;

pub async fn handle_proxy_request(
    State(state): State<AppState>,
    Path(path): Path<String>,
    headers: HeaderMap,
    req: Request<Body>,
) -> Result<Response, StatusCode> {
    // 1. FIREWALL: Check budget BEFORE doing any work
    if !firewall::is_under_budget(&state).await {
        tracing::error!("FIREWALL KILLED REQUEST: Daily budget exceeded.");
        return Err(StatusCode::PAYMENT_REQUIRED);
    }

    // Extract body bytes
    let body_bytes = axum::body::to_bytes(req.into_body(), usize::MAX)
        .await
        .map_err(|_| StatusCode::BAD_REQUEST)?;

    // Parse JSON payload
    let mut payload: serde_json::Value = serde_json::from_slice(&body_bytes)
        .map_err(|_| StatusCode::BAD_REQUEST)?;

    // 2. CACHE: Strip unchanged local files from context
    payload = cache::process_semantic_cache(payload).await;

    // 3. COMPRESSION: Distill long histories locally via Ollama
    payload = compress::distill_history(payload).await;

    // 4. FORWARD: Send the optimized payload to Anthropic/OpenAI
    let target_url = format!("https://api.openai.com/{}", path); // Extrapolate base dynamically based on headers in production
    
    let res = state.http_client.post(&target_url)
        .headers(headers.clone()) // Pass through Auth headers
        .json(&payload)
        .send()
        .await
        .map_err(|_| StatusCode::BAD_GATEWAY)?;

    // 5. UPDATE FIREWALL: (In production, you must parse the SSE stream or headers to count exact usage here)
    firewall::record_usage(&state, 0.01).await; // Mocked cost

    // Stream response back to client
    let mut response_builder = Response::builder().status(res.status());
    for (key, value) in res.headers() {
        response_builder = response_builder.header(key, value);
    }
    
    let body = Body::from_stream(res.bytes_stream());
    Ok(response_builder.body(body).unwrap())
}
```

#### `src/cache.rs`
Semantic caching stub. Diffing logic goes here.
```rust
use serde_json::Value;

pub async fn process_semantic_cache(mut payload: Value) -> Value {
    // Logic: 
    // 1. Iterate over messages looking for code block patterns or XML file tags (e.g. <file name="src/main.rs">)
    // 2. Hash the current local file.
    // 3. Check DB if hash matches previously sent content.
    // 4. If match, replace content with a system instruction: "<TokenWall: Context unchanged. Use cached embedding.>"
    // For now, return payload unmodified.
    payload
}
```

#### `src/compress.rs`
Ollama summarization stub.
```rust
use serde_json::Value;

pub async fn distill_history(mut payload: Value) -> Value {
    // Logic:
    // 1. If payload contains > 10 messages, take messages 1 through N-2.
    // 2. Send to localhost:11434 (Ollama) with prompt: "Summarize this conversation concisely."
    // 3. Replace the middle messages with one synthesized message.
    payload
}
```

#### `src/firewall.rs`
The Kill-Switch logic.
```rust
use crate::AppState;

pub async fn is_under_budget(state: &AppState) -> bool {
    let conn = state.db_pool.lock().unwrap();
    // In production: Query sum of spend for current UTC date.
    let current_spend: f64 = conn.query_row(
        "SELECT COALESCE(SUM(cost), 0.0) FROM usage WHERE date('now') = date(timestamp)",
        [],
        |row| row.get(0),
    ).unwrap_or(0.0);

    current_spend < state.daily_budget
}

pub async fn record_usage(state: &AppState, cost: f64) {
    let conn = state.db_pool.lock().unwrap();
    conn.execute(
        "INSERT INTO usage (cost) VALUES (?1)",
        [cost],
    ).ok();
}
```

#### `src/db.rs`
SQLite Schema.
```rust
use rusqlite::{Connection, Result};

pub fn init_db() -> Result<Connection> {
    let conn = Connection::open("tokenwall.db")?;
    
    // Usage tracking table
    conn.execute(
        "CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            cost REAL NOT NULL
        )",
        [],
    )?;

    // Cache table for file hashes
    conn.execute(
        "CREATE TABLE IF NOT EXISTS file_cache (
            filepath TEXT PRIMARY KEY,
            hash TEXT NOT NULL,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
        )",
        [],
    )?;

    Ok(conn)
}
```

***
**Linus's Final Note to Forge:** The proxy interception in `proxy.rs` is currently returning the `reqwest` byte stream as an Axum body. This works, but LLM clients expect perfect SSE chunks. Watch your chunk alignment when you iterate. Don't build a UI. Build it, run `cargo build --release`, and let's get Vera her GitHub stars. Execute.
