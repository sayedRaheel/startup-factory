#!/bin/bash
set -e

# Clear existing engram directory to start fresh
rm -rf engram

# 1. Initialize the binary project
cargo new engram
cd engram

# 2. Add dependencies
cargo add clap --features derive
cargo add notify
cargo add rusqlite --features bundled
cargo add daemonize
cargo add ignore
cargo add serde --features derive
cargo add serde_json
cargo add chrono
cargo add anyhow
cargo add sha2

# 3. Create the necessary internal files
mkdir -p src
touch src/cli.rs src/daemon.rs src/db.rs src/compressor.rs src/dump.rs src/error.rs
touch .engramignore

# 4. Populate src/cli.rs
cat << 'INNER_EOF' > src/cli.rs
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
INNER_EOF

# 5. Populate src/db.rs
cat << 'INNER_EOF' > src/db.rs
use rusqlite::{Connection, Result};
use std::path::PathBuf;

pub struct DB {
    conn: Connection,
}

impl DB {
    pub fn init(db_path: PathBuf) -> Result<Self> {
        let conn = Connection::open(db_path)?;
        
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

    pub fn get_all_events(&self) -> Result<Vec<(String, String, String, String)>> {
        let mut stmt = self.conn.prepare("SELECT file_path, event_type, timestamp, content_hash FROM file_events ORDER BY timestamp ASC")?;
        let event_iter = stmt.query_map([], |row| {
            Ok((
                row.get(0)?,
                row.get(1)?,
                row.get(2)?,
                row.get(3)?,
            ))
        })?;

        let mut events = Vec::new();
        for event in event_iter {
            events.push(event?);
        }
        Ok(events)
    }
}
INNER_EOF

# 6. Populate src/daemon.rs
cat << 'INNER_EOF' > src/daemon.rs
use anyhow::Result;
use daemonize::Daemonize;
use notify::{Watcher, RecursiveMode, RecommendedWatcher, Config, EventKind};
use std::sync::mpsc::channel;
use std::fs::{self, File};
use std::path::{Path, PathBuf};
use ignore::WalkBuilder;
use sha2::{Sha256, Digest};
use crate::db::DB;

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
            run_watcher_loop()?;
        }
        Err(e) => eprintln!("Error starting daemon: {}", e),
    }

    Ok(())
}

fn get_file_hash(path: &Path) -> String {
    if let Ok(content) = fs::read(path) {
        let mut hasher = Sha256::new();
        hasher.update(&content);
        format!("{:x}", hasher.finalize())
    } else {
        String::new()
    }
}

fn run_watcher_loop() -> Result<()> {
    let db_path = PathBuf::from("/tmp/engram.db");
    let db = DB::init(db_path)?;

    let (tx, rx) = channel();
    let mut watcher = RecommendedWatcher::new(tx, Config::default())?;
    watcher.watch(Path::new("."), RecursiveMode::Recursive)?;

    for res in rx {
        match res {
            Ok(event) => {
                let paths = event.paths;
                let event_type = match event.kind {
                    EventKind::Create(_) => "created",
                    EventKind::Modify(_) => "modified",
                    EventKind::Remove(_) => "deleted",
                    _ => continue,
                };

                for path in paths {
                    let rel_path = path.strip_prefix(Path::new(".")).unwrap_or(&path).to_str().unwrap_or("").to_string();
                    
                    let is_ignored = WalkBuilder::new(".")
                        .hidden(true)
                        .git_ignore(true)
                        .build()
                        .filter_map(|e| e.ok())
                        .all(|e| e.path() != path.as_path());
                    
                    if !is_ignored && !rel_path.is_empty() {
                        let hash = if event_type != "deleted" {
                            get_file_hash(&path)
                        } else {
                            String::new()
                        };
                        
                        let _ = db.log_event(&rel_path, event_type, &hash);
                    }
                }
            },
            Err(_) => continue,
        }
    }
    Ok(())
}
INNER_EOF

# 7. Populate src/dump.rs
cat << 'INNER_EOF' > src/dump.rs
use anyhow::Result;
use crate::db::DB;
use std::path::PathBuf;
use std::fs;

pub fn generate(out: Option<String>) -> Result<()> {
    let db_path = PathBuf::from("/tmp/engram.db");
    if !db_path.exists() {
        println!("No database found. Start the daemon first.");
        return Ok(());
    }

    let db = DB::init(db_path)?;
    let events = db.get_all_events()?;

    let mut output = String::from("# Engram Context Dump\n\n## File Events\n");
    for (path, event_type, timestamp, hash) in events {
        output.push_str(&format!("### {} ({} at {})\n", path, event_type, timestamp));
        output.push_str(&format!("Hash: {}\n\n", hash));
    }

    if let Some(out_path) = out {
        fs::write(&out_path, output)?;
        println!("Dump written to {}", out_path);
    } else {
        println!("{}", output);
    }
    Ok(())
}
INNER_EOF

# 8. Populate src/main.rs
cat << 'INNER_EOF' > src/main.rs
mod cli;
mod daemon;
mod db;
mod compressor;
mod dump;
mod error;

use clap::Parser;
use cli::{Cli, Commands};
use std::fs;
use std::process::Command;

fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    match &cli.command {
        Commands::Start => {
            println!("Starting Engram daemon... It will now run invisibly.");
            daemon::start()?;
        }
        Commands::Stop => {
            println!("Stopping Engram daemon...");
            if let Ok(pid_str) = fs::read_to_string("/tmp/engram.pid") {
                let pid = pid_str.trim();
                let _ = Command::new("kill")
                    .arg("-15")
                    .arg(pid)
                    .status();
                let _ = fs::remove_file("/tmp/engram.pid");
                println!("Daemon stopped.");
            } else {
                println!("Daemon not running.");
            }
        }
        Commands::Dump { out } => {
            dump::generate(out.clone())?;
        }
    }

    Ok(())
}
INNER_EOF

# 9. Populate src/compressor.rs (empty stub for now)
cat << 'INNER_EOF' > src/compressor.rs
pub fn compress(_content: &str) -> String {
    // Basic implementation just to avoid warnings/errors
    _content.to_string()
}
INNER_EOF

# 10. Populate src/error.rs
cat << 'INNER_EOF' > src/error.rs
// Empty stub for now
INNER_EOF

# 11. Compile
cargo build

echo "Done!"
