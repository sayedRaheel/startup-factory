mod cli;
mod compiler;
mod gateway;
mod harness;
mod config;

use clap::Parser;
use std::process::{Command, Stdio};
use tokio::task;
use std::sync::Arc;
use tokio::sync::Mutex;
use crate::harness::proxy::{start_proxy, AppState};

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();
    let cli = cli::Cli::parse();

    match cli.command {
        cli::Commands::Init => {
            std::fs::write(".tetherrules", "strict_mode = true\n").unwrap();
            println!("Tether initialized. Context compiler rules generated.");
        }
        cli::Commands::Run { agent_command, args } => {
            tracing::info!("Compiling strict context...");
            let compiled_context = compiler::compile_context();

            let proxy_port = 8765;
            let state = AppState {
                is_proven: Arc::new(Mutex::new(false)),
                compiled_context,
                real_api_base: std::env::var("OPENAI_BASE_URL")
                    .unwrap_or_else(|_| "https://api.openai.com".to_string()),
            };

            task::spawn(async move {
                start_proxy(state, proxy_port).await;
            });

            tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;

            tracing::info!("Spawning agent inside Tether Sandbox...");
            
            let mut child = Command::new(&agent_command)
                .args(args)
                .env("OPENAI_BASE_URL", format!("http://127.0.0.1:{}", proxy_port))
                .stdout(Stdio::inherit())
                .stderr(Stdio::inherit())
                .spawn()
                .expect("Failed to start agent process");

            let status = child.wait().expect("Agent process crashed");
            tracing::info!("Agent exited with status: {}", status);
        }
    }
}
