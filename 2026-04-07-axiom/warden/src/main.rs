mod cli;
mod executor;
mod ledger;
mod sandbox;

use std::env;
use std::process;

fn main() {
    let args = cli::parse_args();

    match args.command {
        cli::Commands::Run { agent, prompt, verify_cmd } => {
            println!("Starting Warden auto-verification loop...");

            let current_dir = env::current_dir().unwrap_or_else(|err| {
                eprintln!("Failed to get current dir: {}", err);
                process::exit(1);
            });

            let ledger_mgr = ledger::Manager::new(&current_dir);
            let mut state = ledger_mgr.load().unwrap_or_else(|err| {
                eprintln!("Failed to load ledger: {}", err);
                process::exit(1);
            });

            let sb = sandbox::Sandbox::init(&current_dir).unwrap_or_else(|err| {
                eprintln!("Sandbox init failed: {}", err);
                process::exit(1);
            });

            let max_iterations = 3;
            let mut current_prompt = prompt.clone();

            for i in 1..=max_iterations {
                println!("--- Iteration {} ---", i);

                let sandbox_path_str = sb.sandbox_path.to_str().unwrap();

                if let Err(err) = executor::run_agent(sandbox_path_str, &agent, &current_prompt) {
                    println!("Agent failed to run: {}", err);
                    break;
                }

                match executor::verify(sandbox_path_str, &verify_cmd) {
                    Ok(_) => {
                        state.attempts.push(ledger::Attempt {
                            iteration: i,
                            error_trace: None,
                            success: true,
                        });
                        if let Err(err) = ledger_mgr.save(&state) {
                            println!("Warning: Failed to save ledger: {}", err);
                        }

                        if let Err(err) = sb.merge_to_main() {
                            eprintln!("Failed to merge: {}", err);
                            process::exit(1);
                        }
                        println!("Agent task verified and merged successfully.");
                        // Disarm cleanup so that merge_to_main isn't interfered with? No, we need cleanup anyway to remove the branch and worktree
                        // But wait! We merged the branch. If we delete the branch and worktree, it shouldn't affect the merged state in main.
                        break;
                    }
                    Err(err_msg) => {
                        let err_str = err_msg.to_string();
                        state.attempts.push(ledger::Attempt {
                            iteration: i,
                            error_trace: Some(err_str.clone()),
                            success: false,
                        });
                        if let Err(err) = ledger_mgr.save(&state) {
                            println!("Warning: Failed to save ledger: {}", err);
                        }

                        println!("Tests failed. Formatting error trace for next agent iteration...");
                        current_prompt = format!(
                            "Your previous attempt failed. Fix the code to pass the tests.\n\nOriginal prompt: {}\n\nTest Error Output:\n{}",
                            prompt, err_str
                        );
                    }
                }
            }
        }
    }
}
