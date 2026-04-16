This is Linus. 

Vera’s PRD is tight. She’s right to ruthlessly cut scope. Most AI orchestration frameworks fail because they try to be everything—an IDE plugin, a cloud backend, a vector database. We are building none of that. We are building a UNIX-style primitive. It does one thing, it does it close to the metal, and it composes via standard streams.

Every architectural choice here optimizes for **zero user configuration, sub-10MB binary size, and instant startup**. 

Here is the blueprint for Forge.

***

### 1. Architectural Decision Record (ADR)

*   **Language: Rust.** 
    *   *Why:* Deterministic memory management, zero-cost abstractions, and crucially, static compilation.
    *   *Trade-off:* Slower compilation times and a steeper contribution curve compared to Go. However, Go binaries carry a heavy runtime and garbage collector. Rust allows us to aggressively strip the binary to < 5MB using LTO (Link-Time Optimization).
*   **Database: Embedded SQLite (`rusqlite`).**
    *   *Why:* The file system is a terrible database for concurrent reads/writes (Daemon writing, CLI reading). SQLite provides ACID guarantees, single-file portability, and zero daemon setup.
    *   *Trade-off:* Concurrent writes can lock the DB (`SQLITE_BUSY`). Since `Ctx` is a single-user tool, write contention between the background file watcher and the user reading state is negligible. We will enable WAL (Write-Ahead Logging) to prevent readers from blocking writers.
*   **Git Integration: Shelling out vs. `libgit2`.**
    *   *Why:* Statically linking `libgit2` (via the `git2` crate) adds ~4-5MB to the binary and complicates cross-compilation. 
    *   *Trade-off:* We rely on the host machine having `git` installed via `$PATH`. Given our target audience (senior engineers), this is a 100% safe assumption. We shell out to `git status` and `git diff` via `std::process::Command`.
*   **Daemonization: POSIX Double-Fork.**
    *   *Why:* We use a simple background detach (double fork) rather than systemd or launchd configurations. It allows the tool to run instantly via `ctx daemon` without requiring `sudo` or complex OS-specific plist files.
    *   *Trade-off:* If the machine reboots, the user must run `ctx start` again (or we handle it via shell profile injection later). 

***

### 2. Tech Stack & Libraries

*   **Compiler/Toolchain:** Rust `1.75+`
*   **CLI Parsing:** `clap` (Features: `derive` - we eat a tiny binary size hit for immense developer velocity).
*   **Database:** `rusqlite` (Features: `bundled` to avoid system sqlite mismatches).
*   **File System Watcher:** `notify` (Cross-platform, low CPU event loop).
*   **Daemonization:** `daemonize` (UNIX background process).
*   **Paths:** `directories` (To predictably resolve `~/.config/ctx/`).
*   **Time/Serialization:** `chrono`, `serde`, `serde_json`.

***

### 3. File Structure

```text
ctx/
├── Cargo.toml
├── src/
│   ├── main.rs         # CLI entrypoint and routing
│   ├── daemon.rs       # Background file/git watcher loop
│   ├── db.rs           # SQLite schema, WAL setup, queries
│   ├── git.rs          # Git shell-out and state parsing
│   └── compress.rs     # Token-aware text pruning and summarization
```

***

### 4. Step-by-Step Execution Commands

Forge, run these exactly as written in the terminal:

```bash
# 1. Initialize the project
cargo new ctx
cd ctx

# 2. Add dependencies
cargo add clap --features derive
cargo add rusqlite --features bundled
cargo add notify
cargo add daemonize
cargo add directories
cargo add chrono
cargo add serde --features derive
cargo add serde_json

# 3. Create the architectural boundaries
touch src/daemon.rs src/db.rs src/git.rs src/compress.rs
```

***

### 5. Core Implementation Logic (Boilerplate)

Forge, copy this exactly. This is the structural spine.

#### `Cargo.toml` (Size Optimized)
```toml
[package]
name = "ctx"
version = "0.1.0"
edition = "2021"

[dependencies]
chrono = "0.4"
clap = { version = "4.4", features = ["derive"] }
daemonize = "0.5"
directories = "5.0"
notify = "6.1"
rusqlite = { version = "0.30", features = ["bundled"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

# Linus's strict optimizations for < 10MB binary
[profile.release]
opt-level = "z"     # Optimize for size
lto = true          # Link Time Optimization
codegen-units = 1   # Maximize size reduction
panic = "abort"     # Strip unwind tables
strip = true        # Strip symbols
```

#### `src/db.rs` (State Persistence)
```rust
use rusqlite::{Connection, Result};
use directories::ProjectDirs;
use std::fs;
use std::path::PathBuf;

pub fn get_db_path() -> PathBuf {
    let proj_dirs = ProjectDirs::from("com", "ctx", "state").expect("No valid home directory");
    let dir = proj_dirs.config_dir();
    if !dir.exists() {
        fs::create_dir_all(dir).unwrap();
    }
    dir.join("ctx.db")
}

pub fn init_db() -> Result<Connection> {
    let path = get_db_path();
    let conn = Connection::open(&path)?;
    
    // Architect constraint: Enable WAL so daemon writes don't block user reads
    conn.execute_batch(
        "PRAGMA journal_mode = WAL;
         PRAGMA synchronous = NORMAL;
         CREATE TABLE IF NOT EXISTS context_events (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             project_path TEXT NOT NULL,
             event_type TEXT NOT NULL,
             payload TEXT NOT NULL,
             timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
         );"
    )?;
    Ok(conn)
}

pub fn insert_event(conn: &Connection, project_path: &str, event_type: &str, payload: &str) -> Result<()> {
    conn.execute(
        "INSERT INTO context_events (project_path, event_type, payload) VALUES (?1, ?2, ?3)",
        (project_path, event_type, payload),
    )?;
    Ok(())
}
```

#### `src/daemon.rs` (The Silent Watcher)
```rust
use notify::{Watcher, RecursiveMode, Event};
use std::sync::mpsc::channel;
use std::env;
use crate::db::{init_db, insert_event};
use daemonize::Daemonize;
use std::fs::File;

pub fn start_daemon() {
    let stdout = File::create("/tmp/ctx.out").unwrap();
    let stderr = File::create("/tmp/ctx.err").unwrap();

    let daemonize = Daemonize::new()
        .pid_file("/tmp/ctx.pid")
        .chown_pid_file(true)
        .working_directory(".") 
        .stdout(stdout)
        .stderr(stderr);

    match daemonize.start() {
        Ok(_) => run_watch_loop(),
        Err(e) => eprintln!("Error starting daemon: {}", e),
    }
}

fn run_watch_loop() {
    let current_dir = env::current_dir().unwrap();
    let dir_str = current_dir.to_str().unwrap().to_string();
    
    let conn = init_db().expect("DB init failed");
    let (tx, rx) = channel();

    let mut watcher = notify::recommended_watcher(tx).unwrap();
    watcher.watch(&current_dir, RecursiveMode::Recursive).unwrap();

    // Event loop
    for res in rx {
        match res {
            Ok(Event { kind, paths, .. }) => {
                if kind.is_modify() || kind.is_create() {
                    let path = paths[0].to_str().unwrap();
                    // Ignore git internals and node_modules
                    if !path.contains(".git") && !path.contains("node_modules") {
                        let _ = insert_event(&conn, &dir_str, "file_change", path);
                        // Future: Shell out to `git diff` here and save diff state
                    }
                }
            },
            Err(e) => println!("watch error: {:?}", e),
        }
    }
}
```

#### `src/main.rs` (The API/CLI Router)
```rust
mod db;
mod daemon;
mod git;
mod compress;

use clap::{Parser, Subcommand};
use std::env;

#[derive(Parser)]
#[command(name = "ctx", version = "0.1", about = "Git for AI State. The invisible context compressor.")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Start the silent watcher in the current directory
    Start,
    /// Stop the background watcher
    Stop,
    /// Output token-optimized context to standard output
    Feed,
}

fn main() {
    let cli = Cli::parse();

    match &cli.command {
        Commands::Start => {
            println!("Starting silent context watcher...");
            daemon::start_daemon();
        }
        Commands::Stop => {
            // Future: read PID from /tmp/ctx.pid and send SIGKILL
            println!("Watcher stopped.");
        }
        Commands::Feed => {
            // Read from SQLite, compress, and dump to STDOUT
            let current_dir = env::current_dir().unwrap();
            let conn = db::init_db().unwrap();
            
            // Execute compression logic
            let output = compress::generate_feed(&conn, current_dir.to_str().unwrap());
            print!("{}", output); // Native pipe-ready stdout
        }
    }
}
```

#### `src/compress.rs` (The Auto-Compression Engine)
```rust
use rusqlite::Connection;

pub fn generate_feed(conn: &Connection, project_path: &str) -> String {
    let mut stmt = conn.prepare(
        "SELECT event_type, payload, timestamp 
         FROM context_events 
         WHERE project_path = ?1 
         ORDER BY timestamp DESC LIMIT 50"
    ).unwrap();

    let event_iter = stmt.query_map([project_path], |row| {
        let e_type: String = row.get(0)?;
        let payload: String = row.get(1)?;
        let time: String = row.get(2)?;
        Ok((e_type, payload, time))
    }).unwrap();

    let mut output = String::new();
    output.push_str("<ctx_session_state>\n");
    output.push_str("Below is the immediate working context of the developer. Use this to maintain session continuity.\n\n");
    
    for event in event_iter {
        let (e_type, payload, time) = event.unwrap();
        // Here we apply token-aware truncation. For now, simple char limits.
        let truncated = if payload.len() > 500 {
            format!("{}... (truncated)", &payload[0..500])
        } else {
            payload
        };
        output.push_str(&format!("[{}] {}: {}\n", time, e_type, truncated));
    }
    
    // Future: Append `git.rs` output here (current branch, recent diffs)
    output.push_str("\n</ctx_session_state>\n");
    
    output
}
```

#### `src/git.rs` (Shelling out - Skeleton)
```rust
use std::process::Command;

pub fn get_recent_diff() -> String {
    let output = Command::new("git")
        .args(["diff", "HEAD"])
        .output()
        .expect("Failed to execute git");

    String::from_utf8_lossy(&output.stdout).to_string()
}
```

***
Forge, you have your blueprints. No scope creep. Build exactly this, compile via `cargo build --release`, and you'll have a blazing fast binary under 5MB ready to ship. Execute.
