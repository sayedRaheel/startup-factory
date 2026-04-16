use std::process::Command;

pub fn get_recent_diff() -> String {
    // Avoid panic if git isn't installed or command fails
    match Command::new("git").args(["diff", "HEAD"]).output() {
        Ok(output) => String::from_utf8_lossy(&output.stdout).to_string(),
        Err(_) => String::new(),
    }
}
