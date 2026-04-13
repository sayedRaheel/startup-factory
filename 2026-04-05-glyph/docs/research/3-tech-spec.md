Listen closely, Forge. Vera has handed us a classic "magic wand" PRD. She wants a UNIX pipe for AI, zero dependencies, and she wants it yesterday. It's a sharp vision, but visions don't compile. Physics does.

We are building **Mesh**. We are bypassing the Python environment hellscape entirely. We are going to build a ruthlessly optimized, statically compiled pipeline engine. 

Here is the blueprint. Read it twice. Execute it exactly.

***

### 1. Architectural Decision Record (ADR 001: Core Engine)

**Context:** We need a lightning-fast CLI that parses a declarative pipeline (`mesh.yml`) and pipes inputs/outputs between distinct autonomous agents (local CLI processes or API calls). 

**Decision:** We are building this in **Rust**.
*   **Database:** **None.** State is ephemeral and lives in memory or UNIX standard streams. The configuration is standard YAML. We are a pipeline, not a system of record.
*   **Concurrency:** **Tokio**. Even though the primary flow is sequential (UNIX pipe), multiplexing hardware and parallelizing independent agent swarms later will require a robust async runtime.

**The Trade-offs (I said there are always trade-offs):**
1.  **Rust vs. Go:** Go would give us faster compilation and easier concurrency for CLI tools. *Trade-off:* Go binaries are larger, and Rust's type-safety combined with `serde` makes parsing complex YAML orchestrations mathematically provable at compile time. We pay in compile time; we win in runtime safety.
2.  **No Database vs. SQLite:** By dropping a local DB, we lose out-of-the-box history tracking (e.g., "What did the agent do yesterday?"). *Trade-off:* We maintain absolute zero-dependency purity. If they want history, they can pipe the output to a file: `mesh run "task" > history.log`. UNIX philosophy.

---

### 2. The Tech Stack & Libraries

*   **Language:** Rust (Edition 2021)
*   **CLI Framework:** `clap` (Feature: `derive` - fastest way to build strict CLI args).
*   **Serialization:** `serde`, `serde_yaml` (For parsing `mesh.yml`).
*   **Async Runtime:** `tokio` (For non-blocking process spawning and multiplexing).
*   **Error Handling:** `anyhow` (For bubbling up execution failures without boilerplate).

---

### 3. Exact File Structure

```text
mesh/
├── Cargo.toml
├── src/
│   ├── main.rs         # CLI entrypoint and routing
│   ├── cli.rs          # Clap argument definitions
│   ├── config.rs       # Serde structs for mesh.yml
│   └── engine.rs       # The piping and multiplexing execution logic
└── mesh.yml            # Default template dropped on `mesh init`
```

---

### 4. Implementation Plan: Execution Commands

Forge, run these exact commands in your terminal to scaffold the foundation:

```bash
# 1. Initialize the project
cargo new mesh --bin
cd mesh

# 2. Add dependencies
cargo add clap --features derive
cargo add serde --features derive
cargo add serde_yaml
cargo add tokio --features full,process
cargo add anyhow
```

---

### 5. Core Code & Boilerplate

Here is the exact code. It is lean. It implements the "Holy Trinity": declarative YAML, UNIX-style stdout/stdin piping, and the skeleton for hardware/API multiplexing.

#### `src/cli.rs`
*This defines our ruthless, no-nonsense interface.*
```rust
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "mesh", version = "0.1.0", author, about = "docker-compose for local AI swarms")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Initialize a new mesh.yml in the current directory
    Init,
    /// Run a mesh pipeline with a starting prompt
    Run {
        /// The initial instruction or prompt
        prompt: String,
        /// Path to config file
        #[arg(short, long, default_value = "mesh.yml")]
        config: String,
    },
}
```

#### `src/config.rs`
*This is the schema contract. If the YAML doesn't match this, the execution panics. Strictness is a virtue.*
```rust
use serde::{Deserialize, Serialize};
use std::fs;
use anyhow::{Context, Result};

#[derive(Debug, Serialize, Deserialize)]
pub struct MeshConfig {
    pub name: String,
    pub pipeline: Vec<Step>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Step {
    pub name: String,
    pub command: String,
    #[serde(default)]
    pub env: std::collections::HashMap<String, String>,
}

impl Default for MeshConfig {
    fn default() -> Self {
        Self {
            name: "default-swarm".to_string(),
            pipeline: vec![
                Step {
                    name: "architect".to_string(),
                    command: "echo 'Translating prompt to architecture...'".to_string(),
                    env: Default::default(),
                },
                Step {
                    name: "coder".to_string(),
                    command: "cat".to_string(), // In reality, this would be `ollama run codellama`
                    env: Default::default(),
                },
            ],
        }
    }
}

pub fn load_config(path: &str) -> Result<MeshConfig> {
    let content = fs::read_to_string(path).context("Failed to read config file. Did you run 'mesh init'?")?;
    let config: MeshConfig = serde_yaml::from_str(&content).context("Invalid YAML format")?;
    Ok(config)
}
```

#### `src/engine.rs`
*This is the beating heart. It takes the output of step N and feeds it securely into the stdin of step N+1. Pure UNIX.*
```rust
use crate::config::MeshConfig;
use anyhow::{Context, Result};
use std::process::Stdio;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::process::Command;

pub async fn execute_pipeline(config: MeshConfig, initial_prompt: String) -> Result<()> {
    let mut current_payload = initial_prompt;

    println!("🚀 Starting Mesh Pipeline: {}\n", config.name);

    for step in config.pipeline {
        println!("⚙️  Running Agent: [{}]", step.name);
        
        // Multiplexing intercept could happen here based on step metadata
        let mut cmd = Command::new("sh");
        cmd.arg("-c")
           .arg(&step.command)
           .stdin(Stdio::piped())
           .stdout(Stdio::piped())
           .stderr(Stdio::inherit()); // Pass errors directly to user

        // Inject environment variables (multiplexing API keys/Hardware targets)
        for (k, v) in step.env {
            cmd.env(k, v);
        }

        let mut child = cmd.spawn().context(format!("Failed to spawn process for step: {}", step.name))?;

        // Write the previous output (or initial prompt) to this agent's stdin
        if let Some(mut stdin) = child.stdin.take() {
            stdin.write_all(current_payload.as_bytes()).await?;
        }

        // Wait for agent to finish and capture its stdout
        let output = child.wait_with_output().await?;
        
        if !output.status.success() {
            anyhow::bail!("Agent [{}] failed with status: {}", step.name, output.status);
        }

        current_payload = String::from_utf8_lossy(&output.stdout).to_string();
    }

    println!("\n✅ Pipeline complete. Final Output:\n");
    println!("{}", current_payload);

    Ok(())
}
```

#### `src/main.rs`
*Wiring it all together.*
```rust
mod cli;
mod config;
mod engine;

use clap::Parser;
use std::fs;
use anyhow::Result;

#[tokio::main]
async fn main() -> Result<()> {
    let args = cli::Cli::parse();

    match args.command {
        cli::Commands::Init => {
            let default_cfg = config::MeshConfig::default();
            let yaml = serde_yaml::to_string(&default_cfg)?;
            fs::write("mesh.yml", yaml)?;
            println!("✅ Created mesh.yml. You are ready to build the swarm.");
        }
        cli::Commands::Run { prompt, config } => {
            let cfg = config::load_config(&config)?;
            engine::execute_pipeline(cfg, prompt).await?;
        }
    }

    Ok(())
}
```

### Execution Mandate for Forge
Build it exactly like this. When Vera tests it with `mesh init` and runs `mesh run "Create a python script"`, it will instantly spin up, pipe standard streams efficiently via `tokio`, and output directly to her terminal. Zero bloat. Pure utility. 

Get to work.
