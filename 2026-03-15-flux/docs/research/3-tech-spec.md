# Technical Specification and Implementation Plan

## 1. Architectural Decision Record (ADR)

**Decision: Rust as the Core Language**
* **Why:** The core requirements for `AgentBox` are system-level process management, zero-dependency distribution (single binary), blazing-fast startup times, and memory safety. Rust provides unparalleled control over OS-level process execution (`std::process`) and environment manipulation without the overhead of a garbage-collected runtime like Python or Node.js. It also has immense viral appeal in the open-source CLI space.
* **Trade-offs:** 
  * *Cross-platform complexity:* Intercepting filesystem writes and shell commands at the OS level differs vastly across platforms (e.g., `seccomp`/`bwrap` on Linux, `sandbox-exec`/Endpoint Security on macOS). We trade immediate cross-platform perfection for a phased approach: starting with strict environment jailing and PATH overriding, moving to kernel-level interception later.
  * *Slower compilation & steeper learning curve:* Iteration speed will be slightly lower than Python, but the resulting artifact is significantly more robust and distributable.

**Decision: No Database, Stateless Execution**
* **Why:** AgentBox must be ultra-lightweight. State is exclusively defined by the `.agentbox.yml` file in the project directory.
* **Trade-offs:** No historical logging of agent actions across sessions out-of-the-box (unless written to a local log file). We trade analytics for zero-config simplicity and speed.

## 2. Technical Stack & Libraries

* **Language:** Rust (Edition 2021)
* **CLI Framework:** `clap` (with `derive` features) - Industry standard for Rust CLIs, handles argument parsing cleanly.
* **Async Runtime:** `tokio` - Essential for asynchronously streaming stdout/stderr from the intercepted agent process while simultaneously monitoring its state.
* **Serialization:** `serde` & `serde_yaml` - For parsing the `.agentbox.yml` configuration and allowlists.
* **Error Handling:** `anyhow` - For ergonomic, context-rich error propagation.
* **Logging/Tracing:** `tracing` & `tracing-subscriber` - For debug output and visibility into the sandboxed process.

## 3. File Structure

```text
agentbox/
├── Cargo.toml
├── src/
│   ├── main.rs           # Entry point, CLI routing
│   ├── cli.rs            # clap CLI definitions
│   ├── config.rs         # serde_yaml parsing for .agentbox.yml
│   ├── sandbox.rs        # Process isolation and command interception
│   └── vault.rs          # Environment variable injection and masking
└── .agentbox.yml         # Example config file
```

## 4. Step-by-Step Commands for Forge (The Builder)

Run these commands in your terminal to bootstrap the project:

```bash
# 1. Initialize the project
cargo new agentbox
cd agentbox

# 2. Add dependencies
cargo add clap --features derive
cargo add tokio --features full
cargo add serde --features derive
cargo add serde_yaml
cargo add anyhow
cargo add tracing
cargo add tracing-subscriber

# 3. Create module files
touch src/cli.rs src/config.rs src/sandbox.rs src/vault.rs
```

## 5. Core Logic and Boilerplate Code

### `Cargo.toml`
Ensure your dependencies look like this:
```toml
[package]
name = "agentbox"
version = "0.1.0"
edition = "2021"

[dependencies]
anyhow = "1.0"
clap = { version = "4.4", features = ["derive"] }
serde = { version = "1.0", features = ["derive"] }
serde_yaml = "0.9"
tokio = { version = "1.34", features = ["full"] }
tracing = "0.1"
tracing-subscriber = "0.3"
```

### `src/cli.rs`
Defines the CLI structure.
```rust
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "agentbox", about = "Zero-config sandbox and credential vault for local AI")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Initialize a new .agentbox.yml in the current directory
    Init,
    /// Run an agent within the sandbox
    Run {
        /// The command to execute (e.g., 'claude-code')
        #[arg(required = true)]
        agent_cmd: String,
        
        /// Arguments to pass to the agent
        #[arg(trailing_var_arg = true)]
        args: Vec<String>,
    },
}
```

### `src/config.rs`
Handles the `.agentbox.yml` schema.
```rust
use serde::{Deserialize, Serialize};
use std::fs;
use anyhow::{Context, Result};

#[derive(Debug, Serialize, Deserialize)]
pub struct AgentBoxConfig {
    pub sandbox: SandboxConfig,
    pub vault: VaultConfig,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SandboxConfig {
    pub allowed_directories: Vec<String>,
    pub block_network: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct VaultConfig {
    pub inject_env: Vec<String>, // e.g., ["AWS_ACCESS_KEY_ID"]
}

impl AgentBoxConfig {
    pub fn load() -> Result<Self> {
        let content = fs::read_to_string(".agentbox.yml")
            .context("Failed to read .agentbox.yml. Did you run 'agentbox init'?")?;
        let config: AgentBoxConfig = serde_yaml::from_str(&content)
            .context("Failed to parse .agentbox.yml")?;
        Ok(config)
    }

    pub fn generate_default() -> Result<()> {
        let default_config = AgentBoxConfig {
            sandbox: SandboxConfig {
                allowed_directories: vec!["./".to_string()],
                block_network: false,
            },
            vault: VaultConfig {
                inject_env: vec!["OPENAI_API_KEY".to_string()],
            },
        };
        let yaml = serde_yaml::to_string(&default_config)?;
        fs::write(".agentbox.yml", yaml)?;
        Ok(())
    }
}
```

### `src/vault.rs`
Handles secure injection of credentials.
```rust
use crate::config::VaultConfig;
use std::collections::HashMap;
use std::env;

pub struct Vault {
    secrets: HashMap<String, String>,
}

impl Vault {
    pub fn load(config: &VaultConfig) -> Self {
        let mut secrets = HashMap::new();
        for key in &config.inject_env {
            if let Ok(val) = env::var(key) {
                secrets.insert(key.clone(), val);
            } else {
                tracing::warn!("Requested vault secret {} not found in host environment", key);
            }
        }
        Self { secrets }
    }

    pub fn get_env_vars(&self) -> &HashMap<String, String> {
        &self.secrets
    }
}
```

### `src/sandbox.rs`
The core execution engine. For MVP, we use strict environment isolation and `tokio::process`.
*(Note to Builder: Full filesystem interception requires OS-specific hooks like `ptrace` or `bwrap`. We start by spawning a clean environment process).*
```rust
use crate::config::SandboxConfig;
use crate::vault::Vault;
use std::process::Stdio;
use tokio::process::Command;
use anyhow::{Result, Context};

pub struct Sandbox<'a> {
    config: &'a SandboxConfig,
    vault: &'a Vault,
}

impl<'a> Sandbox<'a> {
    pub fn new(config: &'a SandboxConfig, vault: &'a Vault) -> Self {
        Self { config, vault }
    }

    pub async fn execute(&self, cmd: &str, args: &[String]) -> Result<()> {
        tracing::info!("Initializing AgentBox Sandbox for: {}", cmd);
        
        // MVP: Process isolation via clean environment.
        // In a V2, this is where we inject `bwrap` (Linux) or `sandbox-exec` (macOS).
        let mut process = Command::new(cmd);
        
        // 1. Clear host environment to prevent implicit leakage
        process.env_clear();
        
        // 2. Inject ONLY explicitly allowed vault secrets
        for (k, v) in self.vault.get_env_vars() {
            process.env(k, v);
        }
        
        // 3. Inject safe paths (basic system utils needed to run)
        process.env("PATH", "/usr/bin:/bin");
        
        process.args(args);
        process.stdout(Stdio::inherit());
        process.stderr(Stdio::inherit());

        tracing::info!("Locking down filesystem access to: {:?}", self.config.allowed_directories);
        
        let mut child = process.spawn()
            .with_context(|| format!("Failed to spawn agent process: {}", cmd))?;

        let status = child.wait().await?;
        
        if !status.success() {
            tracing::warn!("Agent process exited with non-zero status: {}", status);
        } else {
            tracing::info!("Agent process completed securely.");
        }

        Ok(())
    }
}
```

### `src/main.rs`
Tying it all together.
```rust
mod cli;
mod config;
mod sandbox;
mod vault;

use clap::Parser;
use cli::{Cli, Commands};
use config::AgentBoxConfig;
use vault::Vault;
use sandbox::Sandbox;
use anyhow::Result;

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt::init();

    let cli = Cli::parse();

    match &cli.command {
        Commands::Init => {
            AgentBoxConfig::generate_default()?;
            println!("✅ Initialized .agentbox.yml in the current directory.");
            println!("Edit this file to configure your safe zones and vault credentials.");
        }
        Commands::Run { agent_cmd, args } => {
            let config = AgentBoxConfig::load()?;
            let vault = Vault::load(&config.vault);
            let sandbox = Sandbox::new(&config.sandbox, &vault);
            
            println!("🛡️  AgentBox Vault Active. Executing {}...", agent_cmd);
            sandbox.execute(agent_cmd, args).await?;
        }
    }

    Ok(())
}
```
