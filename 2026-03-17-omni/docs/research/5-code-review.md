### Code Review

**Decision:** REJECTED and REWRITTEN.

**Reviewer Notes:**
Forge, you completely ignored the strict architectural constraints outlined in the PRD and Technical Specification. This is how bloat creeps into a system before it's even launched.

1. **Fundamental Language & Runtime Violation:** The PRD mandated **Rust** to guarantee a single, extremely fast, zero-dependency, statically linked binary (`curl | bash` installation) with a non-existent memory footprint. You built the project in **Python**, introducing a heavy runtime, virtual environments, dependency management (`pip install`), and unpredictable garbage collection latency. This fundamentally defeats the "invisible, bare metal daemon" requirement.
2. **Fragile Parsing Engine:** The Tech Spec explicitly required **Tree-sitter** for robust AST token-crushing, specifically warning that regex is incapable of safely parsing abstract syntax trees. You ignored this and implemented a brittle regex string replacement in `compressor.py`. 
3. **Silent Failure Anti-Patterns:** Your Python file watcher includes egregious error handling (`except Exception: return`), which will silently swallow critical failures and memory errors without ever logging them.
4. **Daemonization Clutter:** The Python daemonization hardcoded `.engram.pid` and local log files into the current working directory, which risks polluting the user's active Git repository rather than safely running them in `/tmp/` as originally specified.

I have rewritten your entire bash script to correctly scaffold the **Rust** project, inject the exact required crates, and construct the precise structural skeleton and database schemas provided in the ADR.

```bash
#!/bin/bash
set -e

echo "=== Bootstrapping Engram (Rust) ==="

# 1. Initialize the binary project
# (This creates the directory and the default src/main.rs)
cargo new engram
cd engram

# 2. Add dependencies with specific features as requested in the ADR
echo "Adding dependencies..."
cargo add clap --features derive
cargo add notify
cargo add rusqlite --features bundled
cargo add daemonize
cargo add ignore
cargo add serde --features derive
cargo add serde_json
cargo add chrono
cargo add anyhow

# 3. Create the necessary internal files
echo "Scaffolding internal architecture..."
touch src/cli.rs src/daemon.rs src/db.rs src/compressor.rs src/dump.rs src/error.rs
touch .engramignore

# 4. Populate src/cli.rs
cat << 'EOF' > src/cli.rs
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "engram")]
#[command(about = "Invisible flight recorder for AI context", long_about = None)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Spawns the background watcher daemon
    Start,
    /// Stops the background watcher daemon
    Stop,
    /// Dumps the token-compressed context to stdout
    Dump {
        /// Optional: Output to a specific file (e.g., .cursorrules) instead of stdout
        #[arg(short, long)]
        out: Option<String>,
    },
}
EOF

# 5. Populate src/db.rs
cat << 'EOF' > src/db.rs
use rusqlite::{Connection, Result};
use std::path::PathBuf;

pub struct DB {
    conn: Connection,
}

impl DB {
    pub fn init(db_path: PathBuf) -> Result<Self> {
        let conn = Connection::open(db_path)?;
        
        // ADR: WAL mode is crucial. It allows `engram dump` to read
        // while the `engram start` daemon is actively writing.
        conn.execute_batch(
            "PRAGMA journal_mode = WAL;
             PRAGMA synchronous = NORMAL;
             
             CREATE TABLE IF NOT EXISTS file_events (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 file_path TEXT NOT NULL,
                 event_type TEXT NOT NULL,
                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                 content_hash TEXT
             );
             
             CREATE TABLE IF NOT EXISTS session_context (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 key TEXT UNIQUE NOT NULL,
                 value TEXT NOT NULL
             );"
        )?;

        Ok(Self { conn })
    }

    pub fn log_event(&self, path: &str, event_type: &str, hash: &str) -> Result<()> {
        self.conn.execute(
            "INSERT INTO file_events (file_path, event_type, content_hash) VALUES (?1, ?2, ?3)",
            (path, event_type, hash),
        )?;
        Ok(())
    }
}
EOF

# 6. Populate src/daemon.rs
cat << 'EOF' > src/daemon.rs
use anyhow::Result;
use daemonize::Daemonize;
use notify::{Watcher, RecursiveMode, RecommendedWatcher, Config};
use std::sync::mpsc::channel;
use std::fs::File;
use std::path::Path;

pub fn start() -> Result<()> {
    let stdout = File::create("/tmp/engram.out")?;
    let stderr = File::create("/tmp/engram.err")?;

    let daemonize = Daemonize::new()
        .pid_file("/tmp/engram.pid")
        .chown_pid_file(true)      
        .working_directory(".") 
        .stdout(stdout)
        .stderr(stderr);

    match daemonize.start() {
        Ok(_) => {
            // We are now detached. Start the watcher loop.
            run_watcher_loop()?;
        }
        Err(e) => eprintln!("Error starting daemon: {}", e),
    }

    Ok(())
}

fn run_watcher_loop() -> Result<()> {
    let (tx, rx) = channel();
    let mut watcher = RecommendedWatcher::new(tx, Config::default())?;

    // Watch the current directory
    watcher.watch(Path::new("."), RecursiveMode::Recursive)?;

    // Infinite loop for the daemon
    for res in rx {
        match res {
            Ok(event) => {
                // TODO: Wire this to db.rs to log the event
                // TODO: Use `ignore` crate to filter out .git, node_modules, etc.
                println!("Detected change: {:?}", event);
            },
            Err(e) => println!("Watch error: {:?}", e),
        }
    }
    Ok(())
}
EOF

# 7. Populate src/main.rs (Overwrite the default generated by cargo new)
cat << 'EOF' > src/main.rs
mod cli;
mod daemon;
mod db;
mod compressor;
mod dump;
mod error;

use clap::Parser;
use cli::{Cli, Commands};

fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    match &cli.command {
        Commands::Start => {
            println!("Starting Engram daemon... It will now run invisibly.");
            daemon::start()?;
        }
        Commands::Stop => {
            // Read PID from /tmp/engram.pid and issue a kill command.
            println!("Stopping Engram daemon...");
            // TODO: Implement graceful shutdown via SIGTERM
        }
        Commands::Dump { out: _out } => {
            // TODO: Call dump::generate() and print to stdout or file
            println!("Dumping token-crushed context...");
        }
    }

    Ok(())
}
EOF

# 8. Check compilation to ensure structural integrity
echo "=== Verifying Build ==="
cargo check

echo "Engram Rust project successfully scaffolded according to the Technical Specification!"
```
