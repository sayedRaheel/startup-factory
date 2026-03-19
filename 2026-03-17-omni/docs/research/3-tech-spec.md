Vera, the boundaries you’ve set here are exactly what keep open-source projects alive past their initial Hacker News launch. Most tools die of obesity; we are going to build a scalpel. 

As the Architect, I look at systems not just for what they do today, but how they degrade tomorrow. A background daemon is a parasite by definition; our job is to make it a symbiotic one. It must consume virtually zero idle CPU, leave no zombie processes, and its storage must never corrupt.

Here is the Technical Specification and Implementation Plan for Forge. 

***

# ARCHITECTURAL DECISION RECORD (ADR)

### 1. Core Language: Rust
*   **Why:** We require absolute control over memory and system threads for a background daemon. A garbage-collected language (Go, Python) introduces unpredictable latency spikes and a larger runtime footprint. Rust compiles to a single, statically-linked binary, making `curl | bash` distribution trivial.
*   **The Trade-off:** Compilation times are longer, and cross-compilation (especially with C-dependencies like SQLite or Tree-sitter) requires robust CI/CD pipelines (e.g., cross, GitHub Actions). The learning curve for open-source contributors is steeper. 

### 2. Storage: Embedded SQLite (`rusqlite` with `bundled` feature)
*   **Why:** It is a zero-config, serverless, single-file database. We get ACID compliance and structured querying of file changes and terminal logs without asking the user to run Docker.
*   **The Trade-off:** SQLite struggles with high-concurrency writes from multiple processes. Since `engram` is a single-user local daemon, we mitigate this by ensuring only the single background daemon writes to the DB, while `engram dump` only performs reads.

### 3. Parsing Engine: Tree-sitter (`tree-sitter` crate)
*   **Why:** Regex is fundamentally incapable of safely parsing abstract syntax trees. Tree-sitter allows us to do intelligent token-crushing (e.g., stripping the implementation details out of a function but keeping the signature and docstrings).
*   **The Trade-off:** Tree-sitter requires C-bindings and parser grammars to be compiled into the binary. This increases the binary size (~10-15MB) and complicates the build process. We accept this cost because the contextual density it provides is the core value proposition of the product.

### 4. Daemonization Strategy: Unix-First (`daemonize` crate)
*   **Why:** High-velocity engineers using AI tools are overwhelmingly on macOS or Linux. We will use standard Unix double-forking to detach the process.
*   **The Trade-off:** This completely drops native Windows support for v1 (Windows requires a different service architecture). Windows users will need WSL2. This is an acceptable constraint to maintain velocity.

---

# EXACT TECH STACK & LIBRARIES

*   **Language:** Rust (Edition 2021)
*   **CLI Router:** `clap` (with `derive` features for clean struct-based routing).
*   **Filesystem Watcher:** `notify` (cross-platform, uses `kqueue` on Mac, `inotify` on Linux).
*   **Storage:** `rusqlite` (with `bundled` feature to avoid requiring the user to have `libsqlite3-dev` installed).
*   **Daemonization:** `daemonize` (Unix double-fork daemon).
*   **File Traversal/Filtering:** `ignore` (seamlessly respects `.gitignore` and our own `.engramignore`).
*   **Serialization:** `serde` and `serde_json`.

---

# EXACT FILE STRUCTURE

```text
engram/
├── Cargo.toml
├── build.rs                  # Optional: For compiling tree-sitter grammars later
├── src/
│   ├── main.rs               # CLI entrypoint and command routing
│   ├── cli.rs                # Clap struct definitions
│   ├── daemon.rs             # Background process loop and File watcher logic
│   ├── db.rs                 # SQLite schema, migrations, and query interfaces
│   ├── compressor.rs         # Token-crushing, Tree-sitter AST trimming
│   ├── dump.rs               # Context extraction and formatting (Markdown output)
│   └── error.rs              # Centralized custom error types
└── .engramignore             # Default ignore patterns for the daemon itself
```

---

# STEP-BY-STEP COMMANDS FOR FORGE

Forge, execute these commands exactly in your terminal to bootstrap the environment.

```bash
# 1. Initialize the binary project
cargo new engram
cd engram

# 2. Add dependencies with specific features
cargo add clap --features derive
cargo add notify
cargo add rusqlite --features bundled
cargo add daemonize
cargo add ignore
cargo add serde --features derive
cargo add serde_json
cargo add chrono
cargo add anyhow # For clean error propagation

# 3. Create the necessary internal files
touch src/cli.rs src/daemon.rs src/db.rs src/compressor.rs src/dump.rs src/error.rs
```

---

# EXACT LOGIC & BOILERPLATE

Forge, populate the following files. This is the structural skeleton. It establishes the database connection, wires the CLI router, and sets up the daemonization process.

### 1. `src/cli.rs`
*Purpose: Define the explicit boundaries of user input.*
```rust
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
```

### 2. `src/db.rs`
*Purpose: Initialize the SQLite connection and ensure schema state.*
```rust
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
```

### 3. `src/daemon.rs`
*Purpose: Detach from the TTY and start the watcher loop.*
```rust
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
```

### 4. `src/main.rs`
*Purpose: The execution router.*
```rust
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
        Commands::Dump { out } => {
            // TODO: Call dump::generate() and print to stdout or file
            println!("Dumping token-crushed context...");
        }
    }

    Ok(())
}
```

Forge, implement this scaffolding exactly. Once this compiles, the foundational infrastructure is complete. We will then inject the `ignore` crate into the `daemon.rs` loop to ensure we aren't indexing `node_modules`, and proceed to wire up `Tree-sitter` in `compressor.rs` for the AST crushing. 

Vera, the foundation is set. It is ruthless, fast, and does exactly what is required.
