I am Linus. 

Vera has defined a ruthlessly pragmatic product. The AI ecosystem is currently drowning in its own abstraction. Python is a fantastic prototyping language, but it is an atrocious distribution vehicle. `AgentMux` will succeed precisely because it rejects the bloated, VM-dependent orchestrator model in favor of a UNIX-philosophy network proxy.

Here is the architectural blueprint. Read it carefully. Every decision carries a cost.

---

### **1. Architectural Decision Record (ADR)**

**Decision 1: Single Static Binary via Rust (Edition 2021)**
*   **Why:** We are distributing to developers who are exhausted by dependency hell. Rust allows us to compile to a single binary with zero external runtime dependencies (`node_modules`, `venv`, etc.). It gives us safe concurrency and C-level network speed.
*   **Trade-off:** Rust's strict typing means parsing arbitrary LLM API payloads (which often contain undocumented or mutating schemas) can be brittle. We mitigate this by treating payloads as opaque `bytes` or generic `serde_json::Value` arrays wherever possible. We are a router, not a parser.

**Decision 2: Combined Proxy & TUI in One Process**
*   **Why:** `tokio` (our async runtime) allows us to seamlessly run a high-throughput HTTP server on a background thread while the main thread drives a `ratatui` terminal interface. This creates the "magic" single-command UX (`agentmux up`).
*   **Trade-off:** If the TUI panics, the proxy goes down with it. We must ensure the UI loop is entirely decoupled from the proxy panic domain, utilizing channels (`mpsc`) or atomic state (`Arc<AtomicUsize>`) for cross-thread telemetry rather than direct memory sharing.

**Decision 3: Layer 7 (HTTP) Proxying over Layer 4 (TCP)**
*   **Why:** To seamlessly route from OpenAI to Ollama, we must rewrite Host headers and intercept 429/500 HTTP status codes to trigger fallbacks. A pure TCP proxy cannot do this. 
*   **Trade-off:** We incur a slight latency penalty by terminating and re-originating HTTP requests. We will use `reqwest` with streaming enabled to immediately pipe Server-Sent Events (SSE) back to the client, minimizing Time-To-First-Token (TTFT) degradation.

---

### **2. Tech Stack & Libraries**

*   **Language:** Rust (Edition 2021)
*   **Async Runtime:** `tokio` (multi-thread, full features)
*   **HTTP Server (Ingress):** `axum` (Lightweight, robust routing)
*   **HTTP Client (Egress):** `reqwest` (with `stream` and `rustls-tls` to avoid OpenSSL system dependencies)
*   **Terminal UI:** `ratatui` + `crossterm` (Immediate mode TUI)
*   **Serialization:** `serde`, `serde_yaml`, `serde_json`
*   **CLI Parsing:** `clap`

---

### **3. File Structure**

```text
agentmux/
├── Cargo.toml
├── agents.yaml
└── src/
    ├── main.rs       (Entrypoint, CLI routing, thread spawning)
    ├── config.rs     (YAML schema and loader)
    ├── state.rs      (Thread-safe telemetry & metrics)
    ├── proxy.rs      (Axum server, fallback logic, stream piping)
    └── tui.rs        (Ratatui render loop)
```

---

### **4. Execution Plan (Step-by-Step Commands)**

Forge, execute these exactly as written to scaffold the environment.

```bash
# 1. Initialize the project
cargo new agentmux
cd agentmux

# 2. Add dependencies (pinning features for minimal bloat)
cargo add tokio -F full
cargo add axum
cargo add reqwest -F stream -F json -F rustls-tls --no-default-features
cargo add ratatui crossterm
cargo add serde -F derive
cargo add serde_yaml serde_json
cargo add clap -F derive
cargo add futures-util # Required for stream handling

# 3. Scaffold the internal modules
touch src/config.rs src/state.rs src/proxy.rs src/tui.rs
```

---

### **5. Core Implementation Boilerplate**

Forge, here is the exact logic mapping. Do not over-engineer the gaps. 

#### **`src/config.rs` (State Definition)**
We need a strict, version-controllable YAML schema.
```rust
use serde::{Deserialize, Serialize};
use std::fs;

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Config {
    pub port: u16,
    pub routes: Vec<Route>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Route {
    pub path: String,
    pub primary: Endpoint,
    pub fallback: Option<Endpoint>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Endpoint {
    pub url: String,
    pub auth_env: Option<String>,
}

impl Config {
    pub fn load(path: &str) -> Self {
        let content = fs::read_to_string(path).unwrap_or_else(|_| panic!("Failed to read {}", path));
        serde_yaml::from_str(&content).expect("Invalid YAML schema")
    }
}
```

#### **`src/state.rs` (Telemetry Bridge)**
This bridges the Axum runtime and the TUI. Use atomics to prevent Mutex locking bottlenecks.
```rust
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

#[derive(Debug, Default)]
pub struct AppMetrics {
    pub total_requests: AtomicUsize,
    pub active_connections: AtomicUsize,
    pub fallbacks_triggered: AtomicUsize,
    pub bytes_transferred: AtomicUsize,
}

pub type SharedState = Arc<AppMetrics>;

impl AppMetrics {
    pub fn inc_req(&self) { self.total_requests.fetch_add(1, Ordering::Relaxed); }
    pub fn inc_fallback(&self) { self.fallbacks_triggered.fetch_add(1, Ordering::Relaxed); }
}
```

#### **`src/proxy.rs` (The Router)**
This handles the ingress, attempts the primary URL, and gracefully catches 429/5xx errors to reroute to the fallback.
```rust
use axum::{
    extract::{State, Request},
    response::{Response, IntoResponse},
    routing::post,
    Router,
};
use reqwest::Client;
use std::sync::Arc;
use crate::{config::Config, state::SharedState};

pub async fn start_server(config: Config, metrics: SharedState) {
    let client = Client::new();
    
    // In a real app, you'd dynamically map `config.routes` here.
    // For boilerplate, we catch all POSTs to a unified handler.
    let app = Router::new()
        .route("/*path", post(handle_request))
        .with_state((config.clone(), metrics.clone(), client));

    let addr = format!("127.0.0.1:{}", config.port);
    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn handle_request(
    State((config, metrics, client)): State<(Config, SharedState, Client)>,
    req: Request,
) -> Response {
    metrics.inc_req();
    
    // 1. Extract path and find matching route in config
    let path = req.uri().path();
    let route = config.routes.iter().find(|r| r.path == path).expect("Route not found");

    // 2. Extract body (treating as opaque bytes to avoid parsing overhead)
    let body_bytes = axum::body::to_bytes(req.into_body(), usize::MAX).await.unwrap();

    // 3. Attempt Primary
    let primary_res = client.post(&route.primary.url)
        .body(body_bytes.clone())
        .send()
        .await;

    match primary_res {
        Ok(res) if res.status().is_success() => {
            // Success! Stream back to client
            return convert_response(res).await;
        }
        _ => {
            // Primary failed or rate-limited. Trigger Fallback.
            if let Some(fallback) = &route.fallback {
                metrics.inc_fallback();
                let fallback_res = client.post(&fallback.url)
                    .body(body_bytes)
                    .send()
                    .await
                    .expect("Fallback also failed");
                return convert_response(fallback_res).await;
            } else {
                return (axum::http::StatusCode::BAD_GATEWAY, "Primary failed, no fallback").into_response();
            }
        }
    }
}

// Helper to pipe reqwest response back to axum
async fn convert_response(res: reqwest::Response) -> Response {
    let mut builder = axum::http::Response::builder().status(res.status());
    for (k, v) in res.headers() { builder = builder.header(k, v); }
    let stream = res.bytes_stream();
    builder.body(axum::body::Body::from_stream(stream)).unwrap()
}
```

#### **`src/tui.rs` (The Dashboard)**
Standard Ratatui setup. It reads `state.rs` without blocking.
```rust
use ratatui::{backend::CrosstermBackend, Terminal, widgets::{Block, Borders, Paragraph}};
use crossterm::{terminal::{enable_raw_mode, disable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen}, execute, event};
use std::{io, time::Duration, sync::atomic::Ordering};
use crate::state::SharedState;

pub async fn run_tui(metrics: SharedState) -> Result<(), io::Error> {
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    loop {
        terminal.draw(|f| {
            let reqs = metrics.total_requests.load(Ordering::Relaxed);
            let fallbacks = metrics.fallbacks_triggered.load(Ordering::Relaxed);
            
            let text = format!("AgentMux Live Traffic\n\nTotal Requests: {}\nFallbacks Triggered: {}", reqs, fallbacks);
            let widget = Paragraph::new(text).block(Block::default().title(" Monitor ").borders(Borders::ALL));
            f.render_widget(widget, f.size());
        })?;

        if event::poll(Duration::from_millis(100))? {
            if let event::Event::Key(key) = event::read()? {
                if key.code == event::KeyCode::Char('q') { break; }
            }
        }
    }

    disable_raw_mode()?;
    execute!(terminal.backend_mut(), LeaveAlternateScreen)?;
    Ok(())
}
```

#### **`src/main.rs` (The Orchestrator)**
Wires the proxy and TUI together gracefully.
```rust
mod config;
mod state;
mod proxy;
mod tui;

use std::sync::Arc;
use clap::Parser;

#[derive(Parser)]
#[command(name = "AgentMux")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(clap::Subcommand)]
enum Commands {
    Init,
    Up,
}

#[tokio::main]
async fn main() {
    let cli = Cli::parse();

    match cli.command {
        Commands::Init => {
            let default_yaml = "port: 8080\nroutes:\n  - path: \"/v1/chat/completions\"\n    primary:\n      url: \"https://api.openai.com/v1/chat/completions\"\n    fallback:\n      url: \"http://localhost:11434/v1/chat/completions\"\n";
            std::fs::write("agents.yaml", default_yaml).unwrap();
            println!("Created agents.yaml. Route configuration ready.");
        }
        Commands::Up => {
            let config = config::Config::load("agents.yaml");
            let metrics = Arc::new(state::AppMetrics::default());

            // Spawn proxy in background
            let proxy_metrics = metrics.clone();
            tokio::spawn(async move {
                proxy::start_server(config, proxy_metrics).await;
            });

            // Run TUI in main thread
            tui::run_tui(metrics).await.unwrap();
        }
    }
}
```

---

**Linus's final note to Forge:** The structure above isolates the network I/O from the rendering loop. It uses opaque byte-streaming to maintain proxy transparency and bypass serialization overhead. Do not add a database. Do not add a web dashboard. Build this exact spec. The beauty is in the constraint. Build it.
