use anyhow::Result;
use notify::{Watcher, RecursiveMode, EventKind};
use notify::event::ModifyKind;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::process::Command;

/// Watches the filesystem. If a file outside `allowed_files` is modified,
/// we execute a git checkout on that file and kill the child process.
pub fn enforce_radius(
    allowed_files: Arc<Vec<PathBuf>>, 
    child_pid: u32, 
    rogue_flag: Arc<Mutex<bool>>
) -> Result<()> {
    let (tx, rx) = std::sync::mpsc::channel();
    let mut watcher = notify::recommended_watcher(tx)?;

    // Watch the current directory
    watcher.watch(&std::env::current_dir()?, RecursiveMode::Recursive)?;

    for res in rx {
        match res {
            Ok(event) => {
                // Only care about Data modification events
                if let EventKind::Modify(ModifyKind::Data(_)) = event.kind {
                    for path in event.paths {
                        if is_unauthorized(&path, &allowed_files) {
                            // 1. Flag as rogue
                            *rogue_flag.lock().unwrap() = true;

                            // 2. Slap the hand away (Revert file)
                            eprintln!("\n🛑 [TETHER] Unauthorized write detected on: {:?}", path);
                            revert_file(&path);

                            // 3. Kill the AI agent
                            kill_process(child_pid);
                            
                            return Ok(()); // Exit bouncer thread
                        }
                    }
                }
            },
            Err(e) => eprintln!("watch error: {:?}", e),
        }
    }

    Ok(())
}

fn is_unauthorized(changed_path: &PathBuf, allowed_files: &[PathBuf]) -> bool {
    let rel_path = match std::env::current_dir() {
        Ok(dir) => changed_path.strip_prefix(&dir).unwrap_or(changed_path).to_path_buf(),
        Err(_) => changed_path.to_path_buf(),
    };

    // Ignore hidden directories (like .git)
    if rel_path.components().any(|c| c.as_os_str().to_string_lossy().starts_with('.')) {
        return false;
    }
    
    // If the changed path is NOT in the allowed list, it's unauthorized
    !allowed_files.contains(changed_path)
}

fn revert_file(path: &PathBuf) {
    eprintln!("⏪ Reverting unauthorized changes...");
    let _ = Command::new("git")
        .args(["checkout", "--"])
        .arg(path)
        .status();
}

#[cfg(unix)]
fn kill_process(pid: u32) {
    unsafe {
        libc::kill(pid as i32, libc::SIGTERM);
    }
}

#[cfg(windows)]
fn kill_process(pid: u32) {
    let _ = Command::new("taskkill")
        .args(["/F", "/PID", &pid.to_string()])
        .status();
}
