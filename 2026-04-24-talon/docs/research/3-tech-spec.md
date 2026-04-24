Linus here. 

Vera’s PRD is aggressive, but mathematically correct. Context windows are growing, but token processing is still the primary bottleneck for agent reasoning speed and cost. Feeding a 10,000-line Webpack error into a $20/M token model is architectural negligence.

Systems outlive the team that built them. If we build this right, Squelch will become the invisible middleware for every local agent framework on the market. 

Here is the blueprint. Forge, your instructions are below.

***

### 1. Architectural Decision Record (ADR)

**Decision:** We will build Squelch in **Rust**, deploying it as a standalone, dependency-free binary running an MCP (Model Context Protocol) JSON-RPC server over `stdio`. 
**Database:** None. Squelch is strictly stateless. 

**Trade-off Matrix:**
*   **Why Rust over Go or Node.js?** Node requires a heavy V8 runtime (100MB+) and breaks zero-config. Go produces decent static binaries (~10-15MB), but its regex engine is notably slower and lacks lookaround support. Rust allows us to compile an ultra-lean (<5MB) binary. Its `regex` crate is built on finite automata, guaranteeing linear time execution—meaning a developer cannot accidentally DoS Squelch by catting a massive minified JS file. 
*   **Why Stateless?** Caching state or secrets introduces lifecycle bugs and staleness. Squelch will read local `.env` files lazily at invocation time. **Trade-off:** Minimal I/O penalty per execution, but guarantees we always redact the *latest* secrets without needing a background watcher daemon.
*   **Secret Redaction Heuristic:** Blindly redacting `.env` values is dangerous (e.g., `PORT=80` would redact the number `80` everywhere). **Trade-off:** We enforce a minimum length of 6 characters for a secret to be registered for redaction. We prioritize system integrity over edge-case micro-secrets.

### 2. Tech Stack & Libraries

*   **Language:** Rust (Edition 2021)
*   **Concurrency / I/O:** `tokio` (Standard async runtime for non-blocking stream handling).
*   **Protocol:** `serde_json` (JSON-RPC 2.0 communication for MCP).
*   **Parsing/Filtration:** `regex` (For stripping ANSI codes, vaulting secrets, and isolating stack traces).
*   **Environment:** `dotenvy` (For reliable `.env` parsing).

### 3. File Structure

Keep it flat. Keep it ruthlessly simple.

```text
squelch/
├── Cargo.toml
└── src/
    ├── main.rs       # Entrypoint, async stdio loop
    ├── mcp.rs        # JSON-RPC 2.0 Models & MCP tool registration
    ├── engine.rs     # Smart truncation & ANSI stripping
    └── vault.rs      # Secret harvesting and redaction
```

### 4. Implementation Commands

Forge, run these exact commands in your terminal to initialize the environment:

```bash
cargo new squelch
cd squelch
cargo add tokio --features full
cargo add serde --features derive
cargo add serde_json
cargo add regex
cargo add dotenvy
cargo add anyhow
```

### 5. Core Implementation Code

Here is the exact boilerplate. Do not add clever abstractions. 

#### `src/vault.rs` (Zero-Config Secret Vaulting)
We harvest `.env` values dynamically and compile a regex to nuke them.

```rust
use regex::{Regex, RegexBuilder};
use std::collections::HashSet;
use std::env;

pub struct Vault {
    redaction_regex: Option<Regex>,
}

impl Vault {
    pub fn new() -> Self {
        let mut secrets = HashSet::new();

        // 1. Harvest from current .env
        if let Ok(iter) = dotenvy::dotenv_iter() {
            for item in iter.flatten() {
                let val = item.1.trim();
                // Trade-off: Do not redact short strings to avoid corrupting standard text
                if val.len() >= 6 {
                    secrets.insert(regex::escape(val));
                }
            }
        }

        // 2. Add standard entropy patterns (AWS keys, JWTs, NPM tokens)
        secrets.insert(r"AKIA[0-9A-Z]{16}".to_string());
        secrets.insert(r"eyJh[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+".to_string());
        secrets.insert(r"npm_[a-zA-Z0-9]{36}".to_string());

        if secrets.is_empty() {
            return Self { redaction_regex: None };
        }

        let pattern = secrets.into_iter().collect::<Vec<_>>().join("|");
        let compiled = RegexBuilder::new(&pattern)
            .size_limit(10 * (1 << 20)) // 10MB limit
            .build()
            .ok();

        Self { redaction_regex: compiled }
    }

    pub fn redact(&self, input: &str) -> String {
        match &self.redaction_regex {
            Some(re) => re.replace_all(input, "[REDACTED_SECRET]").to_string(),
            None => input.to_string(),
        }
    }
}
```

#### `src/engine.rs` (Squelch Engine & Truncation)
Drops ANSI codes and truncates middle bloat.

```rust
use regex::Regex;

pub struct Engine {
    ansi_regex: Regex,
}

impl Engine {
    pub fn new() -> Self {
        Self {
            // Standard regex to strip terminal colors and formatting
            ansi_regex: Regex::new(r"\x1b\[[0-9;]*m").unwrap(),
        }
    }

    pub fn process(&self, raw: &str, max_lines: usize) -> String {
        let clean = self.ansi_regex.replace_all(raw, "");
        let lines: Vec<&str> = clean.lines().collect();

        if lines.len() <= max_lines {
            return clean.to_string();
        }

        // Keep 20% at the top, 80% at the bottom (errors are usually at the bottom)
        let top_count = (max_lines as f32 * 0.2).floor() as usize;
        let bottom_count = max_lines - top_count;
        let omitted = lines.len() - max_lines;

        let mut output = lines[0..top_count].join("\n");
        output.push_str(&format!("\n\n... [SQUELCHED {} LINES] ...\n\n", omitted));
        output.push_str(&lines[lines.len() - bottom_count..].join("\n"));

        output
    }
}
```

#### `src/mcp.rs` (Protocol Models)
Strictly typed JSON-RPC definitions.

```rust
use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Serialize, Deserialize, Debug)]
pub struct JsonRpcRequest {
    pub jsonrpc: String,
    pub id: Option<Value>,
    pub method: String,
    pub params: Option<Value>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct JsonRpcResponse {
    pub jsonrpc: String,
    pub id: Value,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<Value>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct McpTool {
    pub name: String,
    pub description: String,
    pub inputSchema: Value,
}
```

#### `src/main.rs` (The Stdio Interceptor Loop)
The core nervous system. It strictly separates stdout (RPC channel) from stderr (logging channel).

```rust
mod engine;
mod mcp;
mod vault;

use anyhow::Result;
use engine::Engine;
use serde_json::json;
use std::io::{self, BufRead, Write};
use tokio::process::Command;
use vault::Vault;

#[tokio::main]
async fn main() -> Result<()> {
    // Squelch operates via stdin/stdout. Stderr is safe for debugging.
    eprintln!("Squelch MCP Server initialized.");

    let vault = Vault::new();
    let engine = Engine::new();
    let stdin = io::stdin();
    let mut stdout = io::stdout();

    let mut lines = stdin.lock().lines();

    while let Some(Ok(line)) = lines.next() {
        if line.trim().is_empty() {
            continue;
        }

        let req: mcp::JsonRpcRequest = match serde_json::from_str(&line) {
            Ok(r) => r,
            Err(e) => {
                eprintln!("Parse error: {}", e);
                continue;
            }
        };

        let id = req.id.clone().unwrap_or(serde_json::Value::Null);
        let mut response = mcp::JsonRpcResponse {
            jsonrpc: "2.0".to_string(),
            id: id.clone(),
            result: None,
            error: None,
        };

        match req.method.as_str() {
            "initialize" => {
                response.result = Some(json!({
                    "protocolVersion": "2024-11-05",
                    "capabilities": { "tools": {} },
                    "serverInfo": { "name": "squelch", "version": "1.0.0" }
                }));
            }
            "tools/list" => {
                response.result = Some(json!({
                    "tools": [{
                        "name": "squelched_shell",
                        "description": "Execute a shell command with smart truncation and secret redaction.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "command": { "type": "string" }
                            },
                            "required": ["command"]
                        }
                    }]
                }));
            }
            "tools/call" => {
                if let Some(params) = req.params {
                    if params["name"] == "squelched_shell" {
                        let cmd_str = params["arguments"]["command"].as_str().unwrap_or("");
                        
                        // Execute command securely
                        let output = Command::new("sh")
                            .arg("-c")
                            .arg(cmd_str)
                            .output()
                            .await?;

                        let raw_out = String::from_utf8_lossy(&output.stdout);
                        let raw_err = String::from_utf8_lossy(&output.stderr);
                        let combined = format!("STDOUT:\n{}\nSTDERR:\n{}", raw_out, raw_err);

                        // 1. Truncate (keep max 100 lines)
                        let processed = engine.process(&combined, 100);
                        // 2. Redact Secrets
                        let sanitized = vault.redact(&processed);

                        response.result = Some(json!({
                            "content": [{
                                "type": "text",
                                "text": sanitized
                            }]
                        }));
                    }
                }
            }
            _ => {
                response.error = Some(json!({"code": -32601, "message": "Method not found"}));
            }
        }

        // Reply strictly on stdout
        let out_json = serde_json::to_string(&response)?;
        writeln!(stdout, "{}", out_json)?;
        stdout.flush()?;
    }

    Ok(())
}
```

***

**Forge:** The architecture is tight. Run the setup, drop in the Rust files, and build it. Do not attempt to add UI. We build surgical tools, not toys. 

Let me know when the binary is compiled.
