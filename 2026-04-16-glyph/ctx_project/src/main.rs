mod db;
mod daemon;
mod git;
mod compress;

use clap::{Parser, Subcommand};
use std::env;
use std::fs;

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
            // Implemented missing graceful shutdown logic
            if let Ok(pid_str) = fs::read_to_string("/tmp/ctx.pid") {
                let pid = pid_str.trim();
                if let Ok(mut child) = std::process::Command::new("kill").arg("-9").arg(pid).spawn() {
                    let _ = child.wait();
                    let _ = fs::remove_file("/tmp/ctx.pid");
                    println!("Watcher stopped (PID: {}).", pid);
                } else {
                    eprintln!("Failed to execute kill command.");
                }
            } else {
                println!("Watcher is not running or /tmp/ctx.pid not found.");
            }
        }
        Commands::Feed => {
            if let Ok(current_dir) = env::current_dir() {
                if let Ok(conn) = db::init_db() {
                    let output = compress::generate_feed(&conn, current_dir.to_str().unwrap_or(""));
                    print!("{}", output); 
                } else {
                    eprintln!("Failed to initialize database.");
                }
            }
        }
    }
}
