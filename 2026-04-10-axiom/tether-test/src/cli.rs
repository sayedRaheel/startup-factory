use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "tether", version, about = "Zero-trust sandbox for AI coding agents")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Initialize a .tether context rule file in the current directory
    Init,
    /// Run an AI agent within the Tether sandbox
    Run {
        /// The command to start the agent (e.g., "aider", "cline")
        #[arg(required = true)]
        agent_command: String,
        /// Arguments to pass to the agent
        #[arg(last = true)]
        args: Vec<String>,
    },
}
