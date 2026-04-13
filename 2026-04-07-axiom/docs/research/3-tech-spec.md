You want to build a system that survives contact with reality. Good. 

The PRD asks for an "interception" of filesystem mutations. Let's be brutally honest: building a true filesystem interceptor (via FUSE or eBPF) is a multi-month, OS-specific nightmare that violates your PM's mandate for a "lightweight, viral" tool. 

We reject that complexity. Instead, we use **Environment Isolation via Git Worktrees**. We spawn the agent in an isolated, mirrored worktree. It writes locally, believing it is in the main repo. We test the worktree. If it passes, we merge. If it fails, we blast the stderr back into the agent's context.

Here is the architectural blueprint. Forge, your instructions are at the bottom.

---

### 1. Architectural Decision Record (ADR 001)

**Title:** Core Execution, Isolation Strategy, and State Persistence  
**Context:** Warden needs to sandbox AI agents, verify their output, and maintain a state ledger, while remaining a fast, zero-dependency, globally installable binary.  
**Decision:** 
- **Language:** Rust. 
- **Isolation:** `libgit2` (via the `git2` crate) to manage Git Worktrees inside a `.warden/sandbox` directory.
- **State Management:** A local `.warden/ledger.json` file managed via `serde_json`.
**Trade-offs:**
1. **Rust vs. Go:** Go is easier for concurrency, but Rust provides `libgit2` bindings that are significantly more robust for complex git manipulations, plus memory safety for process/pipe management. *Trade-off: Steeper learning curve and longer compile times, but zero runtime bloat.*
2. **Git Worktrees vs. OS-Level Sandboxing (Docker/FUSE):** Docker requires a daemon. FUSE requires OS-level permissions. Git Worktrees are native, require zero elevated privileges, and leverage the exact toolchain the developer already has installed. *Trade-off: We rely on the agent respecting the Current Working Directory (CWD). If a rogue agent uses hardcoded absolute paths, it could escape the sandbox. Acceptable risk for V1.*
3. **JSON Ledger vs. SQLite:** SQLite is ACID compliant. JSON is not. However, Warden runs synchronously for a single developer. *Trade-off: We lose concurrent write safety, but we gain a transparent state file developers can easily `cat`, `jq`, or manually edit.*

---

### 2. Tech Stack & Libraries

- **Language:** Rust (Edition 2021)
- **CLI Interface:** `clap` (feature: `derive`) - Declarative, strict argument parsing.
- **Version Control Engine:** `git2` - Headless git operations (Worktrees, Commits, Merges).
- **Serialization:** `serde`, `serde_json` - For the `.warden` state ledger.
- **Process Management:** `std::process::Command` - Standard library is sufficient for piping stdout/stderr.
- **Error Handling:** `anyhow` (for application-level errors) and `thiserror` (for domain errors).
- **Observability:** `tracing` and `tracing-subscriber` - Because `println!` is for amateurs.

---

### 3. File Structure

```text
warden/
├── Cargo.toml
├── src/
│   ├── main.rs         # Entry point, CLI routing, Tracing setup
│   ├── cli.rs          # Clap struct definitions
│   ├── sandbox.rs      # Git worktree initialization, commit, and merge logic
│   ├── executor.rs     # Subprocess spawning, stdout/stderr capture, test execution
│   ├── ledger.rs       # Read/Write of the .warden/ledger.json file
│   └── error.rs        # Custom domain errors (Validation, Git, IO)
```

---

### 4. Step-by-Step Initialization Commands

Forge, run exactly this in your terminal:

```bash
# 1. Initialize the project
cargo new warden
cd warden

# 2. Add core dependencies
cargo add clap --features derive
cargo add git2
cargo add serde --features derive
cargo add serde_json
cargo add anyhow
cargo add thiserror

# 3. Add observability dependencies
cargo add tracing
cargo add tracing-subscriber --features env-filter

# 4. Create the architectural boundaries
touch src/cli.rs src/sandbox.rs src/executor.rs src/ledger.rs src/error.rs
```

---

### 5. Core Logic & Boilerplate

Forge, here is the boilerplate. I have stubbed out the exact structural boundaries. Fill in the implementation details.

#### `src/cli.rs`
```rust
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
        #[arg(short, long)]
        verify_cmd: String,
    },
}
```

#### `src/ledger.rs`
```rust
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
```

#### `src/sandbox.rs`
```rust
use git2::{Repository, WorktreeAddOptions};
use std::path::{Path, PathBuf};
use anyhow::{Result, Context};
use tracing::info;

pub struct Sandbox {
    pub root_repo: Repository,
    pub sandbox_path: PathBuf,
    pub branch_name: String,
}

impl Sandbox {
    pub fn init<P: AsRef<Path>>(workspace_root: P) -> Result<Self> {
        let repo = Repository::discover(workspace_root.as_ref())
            .context("Not a git repository. Warden requires a git repository to manage worktrees.")?;
        
        let branch_name = format!("warden-sandbox-{}", std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH)?.as_secs());
        let sandbox_path = workspace_root.as_ref().join(".warden").join("sandbox");

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
        })
    }

    pub fn merge_to_main(&self) -> Result<()> {
        info!("Tests passed. Merging {} into main workspace...", self.branch_name);
        // TO FORGE: Implement the git merge logic here.
        // 1. Commit all changes in the sandbox_path.
        // 2. Checkout main repo branch.
        // 3. Merge sandbox branch.
        // 4. Clean up worktree.
        Ok(())
    }

    pub fn cleanup(&self) -> Result<()> {
        info!("Destroying ephemeral sandbox...");
        if self.sandbox_path.exists() {
            std::fs::remove_dir_all(&self.sandbox_path)?;
        }
        // TO FORGE: Prune git worktree via git2
        Ok(())
    }
}
```

#### `src/executor.rs`
```rust
use std::process::{Command, Stdio};
use std::path::Path;
use anyhow::{Result, bail};
use tracing::{info, error};

pub struct Executor;

impl Executor {
    /// Executes the AI agent in the isolated sandbox directory
    pub fn run_agent<P: AsRef<Path>>(sandbox_path: P, agent_cmd: &str, prompt: &str) -> Result<()> {
        info!("Spawning agent: {} with prompt: {}", agent_cmd, prompt);
        
        // TO FORGE: Handle agent-specific syntax. 
        // For now, assuming the agent takes the prompt as the last argument.
        let status = Command::new(agent_cmd)
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
            error!("Verification failed:\n{}", stderr);
            Err(stderr)
        }
    }
}
```

#### `src/main.rs`
```rust
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
```

Forge, the architectural boundaries are drawn. The trade-offs have been calculated. Execute this cleanly. No bloated dependencies. Do not alter the core loop. Go.
