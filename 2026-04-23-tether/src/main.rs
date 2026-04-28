use anyhow::Result;
use clap::Parser;
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;

mod bouncer;
mod profiler;

#[derive(Parser, Debug)]
#[command(name = "tether", version = "1.0", about = "Ruthless AI Agent Bouncer")]
struct Args {
    /// The semantic intent of the task
    #[arg(short, long)]
    intent: String,

    /// The agent command to run (e.g., aider, cursor)
    #[arg(trailing_var_arg = true, required = true)]
    agent_cmd: Vec<String>,
}

fn main() -> Result<()> {
    let args = Args::parse();

    println!("🔒 Tether initializing...");
    
    // 1. Profile the Blast Radius
    let allowed_files = profiler::build_blast_radius(&args.intent)?;
    println!("🎯 Locked target scope to: {:?}", allowed_files);

    // Shared state to allow the bouncer to kill the agent if it goes rogue
    let allowed_files_arc = Arc::new(allowed_files);
    let rogue_flag = Arc::new(Mutex::new(false));

    // 2. Start the Agent Subprocess
    let mut child = Command::new(&args.agent_cmd[0])
        .args(&args.agent_cmd[1..])
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .spawn()
        .expect("Failed to execute agent command");

    let child_id = child.id();

    // 3. Start the Bouncer in a background thread
    let bouncer_flag = Arc::clone(&rogue_flag);
    let bouncer_files = Arc::clone(&allowed_files_arc);
    
    thread::spawn(move || {
        if let Err(e) = bouncer::enforce_radius(bouncer_files, child_id, bouncer_flag) {
            eprintln!("Bouncer error: {}", e);
        }
    });

    // 4. Wait for the agent to finish
    let _status = child.wait()?;

    if *rogue_flag.lock().unwrap() {
        eprintln!("🚨 Tether intercepted unauthorized changes. Agent terminated.");
        std::process::exit(1);
    }

    println!("✅ Task completed within permitted scope.");
    Ok(())
}
