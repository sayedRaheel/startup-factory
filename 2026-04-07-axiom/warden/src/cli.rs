use clap::{Parser, Subcommand};

#[derive(Parser, Debug)]
#[command(author, version, about = "Warden - Ephemeral execution firewall for local agents", long_about = None)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand, Debug)]
pub enum Commands {
    /// Run an agent within the Warden sandbox
    Run {
        /// The agent command to execute
        #[arg(long)]
        agent: String,

        /// The task/prompt for the agent
        #[arg(long)]
        prompt: String,

        /// The test command to verify
        #[arg(long = "verify-cmd")]
        verify_cmd: String,
    },
}

pub fn parse_args() -> Cli {
    Cli::parse()
}
