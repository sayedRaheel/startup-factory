Hey Forge, 

I see the Tech Spec laid out the architecture beautifully, but the provided setup instructions were just a sequential list of interactive terminal commands. If we are automating the scaffolding of this project, we need a robust bash script—not just a copy-paste snippet. 

As a build engineer, I look for scripts that are resilient, idempotent, and programmatic. Here are the glaring issues I fixed to turn those basic instructions into a production-grade bootstrap script:

1. **Missing Safe-Guards (The Golden Rule of Bash):** I added `set -euo pipefail`. If `cargo new` fails for any reason (e.g., the directory already exists), the original commands would blindly proceed to run `cd mesh` (which fails), and then run `cargo add` in the wrong directory. This prevents cascading failures.
2. **Environment Validation:** Added a check to ensure `cargo` is actually installed before we start trying to invoke it.
3. **Idempotency:** Added a check to see if the `mesh` directory already exists. If it does, we clean it up so the script can be run multiple times safely without throwing errors.
4. **Programmatic File Generation:** The Tech Spec showed the file contents but didn't write them. I utilized Here-Docs (`cat << 'EOF' > ...`) to actually write the Rust source files directly to the disk, completely automating the scaffolding phase.

Here is the fully rewritten, bulletproof bootstrap script.

```bash
#!/usr/bin/env bash
# Unofficial Bash Strict Mode
set -euo pipefail

echo "🚀 Bootstrapping Mesh: The UNIX pipe for AI swarms..."

# 1. Dependency Check
if ! command -v cargo &> /dev/null; then
    echo "❌ Error: 'cargo' is not installed."
    echo "Please install Rust (https://rustup.rs/) and try again."
    exit 1
fi

# 2. Project Initialization (with idempotency)
if [ -d "mesh" ]; then
    echo "⚠️  Directory 'mesh' already exists. Removing it for a clean bootstrap..."
    rm -rf mesh
fi

echo "📦 Initializing cargo project..."
cargo new mesh --bin
cd mesh

# 3. Add Dependencies
echo "📥 Adding dependencies..."
cargo add clap --features derive
cargo add serde --features derive
cargo add serde_yaml
cargo add tokio --features full,process
cargo add anyhow

# 4. Write Core Code
echo "✍️  Writing source files..."

cat << 'EOF' > src/cli.rs
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
EOF

cat << 'EOF' > src/config.rs
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
EOF

cat << 'EOF' > src/engine.rs
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
EOF

cat << 'EOF' > src/main.rs
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
EOF

# 5. Format and verify
if command -v cargo-fmt &> /dev/null || cargo fmt --version &> /dev/null; then
    echo "🧹 Formatting codebase..."
    cargo fmt
fi

echo "✅ Mesh bootstrap complete!"
echo ""
echo "Next Steps:"
echo "  cd mesh"
echo "  cargo run -- init"
echo "  cargo run -- run \"Create a python script\""
```
