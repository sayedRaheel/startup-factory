use std::process::Command;

pub fn run_agent(sandbox_path: &str, agent_cmd: &str, prompt: &str) -> Result<(), Box<dyn std::error::Error>> {
    println!("Spawning agent: {}", agent_cmd);
    
    let parts: Vec<&str> = agent_cmd.split_whitespace().collect();
    if parts.is_empty() {
        return Err("empty agent command".into());
    }

    let prog = parts[0];
    let mut args: Vec<&str> = parts[1..].to_vec();
    args.push(prompt);

    let status = Command::new(prog)
        .args(args)
        .current_dir(sandbox_path)
        .status()?;

    if !status.success() {
        return Err(format!("agent execution failed with status: {}", status).into());
    }

    Ok(())
}

pub fn verify(sandbox_path: &str, verify_cmd: &str) -> Result<(), Box<dyn std::error::Error>> {
    println!("Running verification suite: {}", verify_cmd);

    let parts: Vec<&str> = verify_cmd.split_whitespace().collect();
    if parts.is_empty() {
        return Err("empty verify command".into());
    }

    let output = Command::new(parts[0])
        .args(&parts[1..])
        .current_dir(sandbox_path)
        .output()?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let stdout = String::from_utf8_lossy(&output.stdout);
        let mut err_msg = format!("Verification failed:\n{}", stderr);
        if stderr.trim().is_empty() {
            err_msg = format!("Verification failed:\n{}", stdout);
        }
        println!("{}", err_msg);
        return Err(err_msg.into());
    }

    Ok(())
}
