### Code Review

**Decision:** Rewritten entirely due to glaring architectural violations.

**Reviewer Notes:**
Forge, the generated script fundamentally failed to follow the Architecture Decision Record (ADR 001) outlined in the Tech Spec. The spec explicitly mandated **Rust** to leverage bare-metal performance, memory safety, and `libgit2` bindings, and strictly forbade alternate runtimes like Go. Despite being provided with the exact `cargo` initialization commands and Rust boilerplate, the script was written entirely in Go (`go mod init`, `main.go`, etc.). 

I have completely rewritten the builder script to enforce the Tech Spec:
1. **Enforced Rust Ecosystem:** Initialized the project with `cargo new warden` and added the mandated dependencies (`clap`, `git2`, `serde`, `anyhow`, `tracing`, etc.).
2. **Applied Correct Boilerplate:** Inserted the exact Rust structural boundaries provided in the spec (`cli.rs`, `sandbox.rs`, `executor.rs`, `ledger.rs`, `main.rs`).
3. **Implemented Missing Logic:** 
   - Completed the Git worktree merge and cleanup logic inside `sandbox.rs` (combining `git2` for worktree creation and `std::process::Command` for robust commit/merge operations).
   - Handled process standard I/O streams in `executor.rs` to correctly capture and combine `stdout` and `stderr` for the AI agent's error loop.
4. **Compiled Native Binary:** Modified the script to compile the Rust binary (`cargo build --release`) and correctly expose it to the testing suite.

Here is the fully compliant, spec-aligned builder script.

```bash
#!/usr/bin/env bash
set -e

echo "Starting Warden Environment Construction..."

# 1. Project directories setup
rm -rf warden docs
mkdir -p docs/research

# 2. Setup Rust module
cargo new warden
cd warden

cargo add clap --features derive
cargo add git2
cargo add serde --features derive
cargo add serde_json
cargo add anyhow
cargo add thiserror
cargo add tracing
cargo add tracing-subscriber --features env-filter

# 3. Generating Source Code
echo "Generating src files..."
mkdir -p src

cat << 'EOF' > src/main.rs
mod cli;
mod error;
mod executor;
mod ledger;
mod sandbox;

use clap::Parser;
use cli::{Cli, Commands};
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;
use anyhow::Result;

fn main() -> Result<()> {
    let subscriber = FmtSubscriber::builder()
        .with_max_level(Level::INFO)
        .finish();
    tracing::subscriber::set_global_default(subscriber)?;

    let cli = Cli::parse();

    match &cli.command {
        Commands::Run { agent, prompt, verify_cmd } => {
            info!("Starting Warden auto-verification loop...");
            
            let current_dir = std::env::current_dir()?;
            let mut ledger_mgr = ledger::LedgerManager::new(&current_dir);
            let mut state = ledger_mgr.load()?;
            
            // 1. Init Sandbox
            let sandbox = sandbox::Sandbox::init(&current_dir)?;

            let max_iterations = 3;
            let mut current_prompt = prompt.clone();

            for iteration in 1..=max_iterations {
                info!("--- Iteration {} ---", iteration);
                
                // 2. Execute Agent
                if let Err(e) = executor::Executor::run_agent(&sandbox.sandbox_path, agent, &current_prompt) {
                    tracing::error!("Agent failed to run: {}", e);
                    break;
                }

                // 3. Verify
                match executor::Executor::verify(&sandbox.sandbox_path, verify_cmd) {
                    Ok(_) => {
                        // 4a. Success -> Merge
                        state.attempts.push(ledger::Attempt { iteration, error_trace: None, success: true });
                        ledger_mgr.save(&state)?;
                        sandbox.merge_to_main()?;
                        info!("Agent task verified and merged successfully.");
                        break;
                    }
                    Err(stderr) => {
                        // 4b. Failure -> Update Prompt & Ledger
                        state.attempts.push(ledger::Attempt { iteration, error_trace: Some(stderr.clone()), success: false });
                        ledger_mgr.save(&state)?;
                        
                        info!("Tests failed. Formatting error trace for next agent iteration...");
                        current_prompt = format!(
                            "Your previous attempt failed. Fix the code to pass the tests.\n\nOriginal prompt: {}\n\nTest Error Output:\n{}",
                            prompt, stderr
                        );
                    }
                }
            }

            // Always cleanup
            sandbox.cleanup()?;
        }
    }

    Ok(())
}
EOF

cat << 'EOF' > src/cli.rs
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "warden", version, about = "Ephemeral execution firewall for local agents", long_about = None)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Run an agent inside the Warden sandbox
    Run {
        /// The agent command to execute (e.g., "goose")
        #[arg(short, long)]
        agent: String,

        /// The task/prompt for the agent
        #[arg(short, long)]
        prompt: String,

        /// The test command to verify the agent's work (e.g., "npm test")
        #[arg(long)]
        verify_cmd: String,
    },
}
EOF

cat << 'EOF' > src/sandbox.rs
use git2::{Repository, WorktreeAddOptions};
use std::path::{Path, PathBuf};
use anyhow::{Result, Context, bail};
use tracing::info;
use std::process::Command;

pub struct Sandbox {
    pub root_repo: Repository,
    pub sandbox_path: PathBuf,
    pub branch_name: String,
    pub workspace_root: PathBuf,
}

impl Sandbox {
    pub fn init<P: AsRef<Path>>(workspace_root: P) -> Result<Self> {
        let root_path = workspace_root.as_ref().to_path_buf();
        let repo = Repository::discover(&root_path)
            .context("Not a git repository. Warden requires a git repository to manage worktrees.")?;
        
        let branch_name = format!("warden-sandbox-{}", std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH)?.as_secs());
        let sandbox_path = root_path.join(".warden").join("sandbox");

        // Clean up previous sandbox if it exists
        if sandbox_path.exists() {
            std::fs::remove_dir_all(&sandbox_path)?;
        }

        info!("Creating ephemeral git worktree at {:?}", sandbox_path);
        
        let mut opts = WorktreeAddOptions::new();
        // Create a new branch for the sandbox
        let head = repo.head()?.peel_to_commit()?;
        let branch = repo.branch(&branch_name, &head, false)?;
        
        repo.worktree(&branch_name, &sandbox_path, Some(&opts))?;

        Ok(Self {
            root_repo: repo,
            sandbox_path,
            branch_name,
            workspace_root: root_path,
        })
    }

    pub fn merge_to_main(&self) -> Result<()> {
        info!("Tests passed. Merging {} into main workspace...", self.branch_name);
        
        // 1. Commit all changes in the sandbox_path.
        let add_status = Command::new("git")
            .args(["add", "."])
            .current_dir(&self.sandbox_path)
            .status()?;
        if !add_status.success() { bail!("Failed to git add"); }

        let status_out = Command::new("git")
            .args(["status", "--porcelain"])
            .current_dir(&self.sandbox_path)
            .output()?;
            
        if !status_out.stdout.is_empty() {
            let commit_status = Command::new("git")
                .args(["commit", "-m", "Warden automated commit"])
                .current_dir(&self.sandbox_path)
                .status()?;
            if !commit_status.success() { bail!("Failed to git commit"); }
        }

        // 3. Merge sandbox branch
        let merge_status = Command::new("git")
            .args(["merge", "--ff-only", &self.branch_name])
            .current_dir(&self.workspace_root)
            .status()?;
        if !merge_status.success() { bail!("Failed to git merge"); }

        Ok(())
    }

    pub fn cleanup(&self) -> Result<()> {
        info!("Destroying ephemeral sandbox...");
        
        Command::new("git")
            .args(["worktree", "remove", "-f", &self.sandbox_path.to_string_lossy()])
            .current_dir(&self.workspace_root)
            .status()?;

        Command::new("git")
            .args(["branch", "-D", &self.branch_name])
            .current_dir(&self.workspace_root)
            .status()?;

        if self.sandbox_path.exists() {
            let _ = std::fs::remove_dir_all(&self.sandbox_path);
        }
        Ok(())
    }
}
EOF

cat << 'EOF' > src/executor.rs
use std::process::{Command, Stdio};
use std::path::Path;
use anyhow::{Result, bail};
use tracing::{info, error};

pub struct Executor;

impl Executor {
    /// Executes the AI agent in the isolated sandbox directory
    pub fn run_agent<P: AsRef<Path>>(sandbox_path: P, agent_cmd: &str, prompt: &str) -> Result<()> {
        info!("Spawning agent: {} with prompt: {}", agent_cmd, prompt);
        
        let mut parts = agent_cmd.split_whitespace();
        let program = parts.next().unwrap_or_default();
        let args: Vec<&str> = parts.collect();

        let status = Command::new(program)
            .args(args)
            .arg(prompt)
            .current_dir(sandbox_path)
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit())
            .status()?;

        if !status.success() {
            bail!("Agent execution failed");
        }
        Ok(())
    }

    /// Runs the verification test suite. Returns Ok(()) if passes, Err(stderr) if fails.
    pub fn verify<P: AsRef<Path>>(sandbox_path: P, verify_cmd: &str) -> std::result::Result<(), String> {
        info!("Running verification suite: {}", verify_cmd);
        
        let mut parts = verify_cmd.split_whitespace();
        let program = parts.next().unwrap_or_default();
        let args: Vec<&str> = parts.collect();

        let output = Command::new(program)
            .args(args)
            .current_dir(sandbox_path)
            .output()
            .map_err(|e| e.to_string())?;

        if output.status.success() {
            Ok(())
        } else {
            let stderr = String::from_utf8_lossy(&output.stderr).to_string();
            let stdout = String::from_utf8_lossy(&output.stdout).to_string();
            let combined = format!("STDOUT:\n{}\nSTDERR:\n{}", stdout, stderr);
            error!("Verification failed:\n{}", combined);
            Err(combined)
        }
    }
}
EOF

cat << 'EOF' > src/ledger.rs
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use anyhow::{Result, Context};

#[derive(Debug, Serialize, Deserialize, Default)]
pub struct Ledger {
    pub task: String,
    pub attempts: Vec<Attempt>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Attempt {
    pub iteration: u32,
    pub error_trace: Option<String>,
    pub success: bool,
}

pub struct LedgerManager {
    filepath: PathBuf,
}

impl LedgerManager {
    pub fn new<P: AsRef<Path>>(workspace_root: P) -> Self {
        let warden_dir = workspace_root.as_ref().join(".warden");
        if !warden_dir.exists() {
            fs::create_dir_all(&warden_dir).expect("Failed to create .warden directory");
        }
        Self {
            filepath: warden_dir.join("ledger.json"),
        }
    }

    pub fn load(&self) -> Result<Ledger> {
        if !self.filepath.exists() {
            return Ok(Ledger::default());
        }
        let data = fs::read_to_string(&self.filepath)?;
        let ledger: Ledger = serde_json::from_str(&data)?;
        Ok(ledger)
    }

    pub fn save(&self, ledger: &Ledger) -> Result<()> {
        let data = serde_json::to_string_pretty(ledger)?;
        fs::write(&self.filepath, data).context("Failed to write ledger file")?;
        Ok(())
    }
}
EOF

cat << 'EOF' > src/error.rs
use thiserror::Error;

#[derive(Error, Debug)]
pub enum WardenError {
    #[error("Validation error: {0}")]
    Validation(String),
}
EOF

echo "Building Warden Rust binary..."
cargo build --release
cp target/release/warden .
cd ..

# 4. Generate README.md
cat << 'EOF' > README.md
# Warden

Ephemeral execution firewall for local agents. Warden isolates agent workflows using Git worktrees, verifies them through a user-provided command, and safely merges only successful attempts.

### Problem Statement
Running autonomous LLM agents against local codebases is dangerous. They frequently overwrite working logic with hallucinated dependencies, make unverified breaking changes, and corrupt state. We need a zero-dependency, globally installable firewall that confines agents to verified sandboxes and merges changes strictly upon test success.

### Research & Architecture
* [Scout Analysis](./docs/research/1-scout-analysis.md)
* [PRD](./docs/research/2-prd.md)
* [Tech Spec](./docs/research/3-tech-spec.md)
* [Builder Code](./docs/research/4-builder-code.md)
EOF

# 5. Generate Test Execution Script
cat << 'EOF' > test.sh
#!/usr/bin/env bash
set -e

echo "Setting up Warden test environment sandbox..."
rm -rf test_env
mkdir -p test_env
cd test_env

# Initialize dummy workspace
git init
git config user.email "test@warden.local"
git config user.name "Warden Test"

cat << 'INNER_EOF' > target.txt
buggy content
INNER_EOF

cat << 'INNER_EOF' > test_target.sh
#!/usr/bin/env bash
if grep -q "fixed content" target.txt; then
    echo "Test passed!"
    exit 0
else
    echo "Test failed: content is still buggy"
    exit 1
fi
INNER_EOF
chmod +x test_target.sh

cat << 'INNER_EOF' > dummy_agent.sh
#!/usr/bin/env bash
PROMPT="${@: -1}"
echo "Agent Received Prompt: $PROMPT"
if [[ "$PROMPT" == *"Your previous attempt failed"* ]]; then
    echo "Agent iteration 2: Fixing the file..."
    echo "fixed content" > target.txt
else
    echo "Agent iteration 1: Simulating hallucination/bug..."
    echo "still buggy content" > target.txt
fi
INNER_EOF
chmod +x dummy_agent.sh

git add target.txt test_target.sh dummy_agent.sh
git commit -m "Initial commit"

echo "Executing Warden firewall over dummy agent..."
../warden/warden run \
    --agent "./dummy_agent.sh" \
    --prompt "Fix the target.txt file" \
    --verify-cmd "./test_target.sh"

echo "Validating git merge integrity..."
if grep -q "fixed content" target.txt; then
    echo "SUCCESS: Agent bug was fixed and securely merged into main."
else
    echo "FAILURE: Fix was not merged."
    exit 1
fi

echo "Validating ledger state..."
if grep -q '"success": true' .warden/ledger.json; then
    echo "SUCCESS: Ledger correctly recorded the successful loop."
else
    echo "FAILURE: Ledger state invalid."
    exit 1
fi

echo "All tests completed with Exit Code 0."
EOF
chmod +x test.sh

echo "Build complete. Running self-tests..."
./test.sh
```
