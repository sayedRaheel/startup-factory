use std::process::Stdio;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command;
use tokio::sync::mpsc::{Sender, Receiver};
use crate::app::LogEvent;

pub async fn run_and_monitor(cmd_args: Vec<String>, tx: Sender<LogEvent>, mut kill_rx: Receiver<()>) {
    if cmd_args.is_empty() {
        let _ = tx.send(LogEvent::Stdout("Error: No command provided".into())).await;
        return;
    }

    let mut command = Command::new(&cmd_args[0]);
    if cmd_args.len() > 1 {
        command.args(&cmd_args[1..]);
    }
    
    command.stdout(Stdio::piped());
    command.stderr(Stdio::piped());

    let mut child = match command.spawn() {
        Ok(c) => c,
        Err(e) => {
            let _ = tx.send(LogEvent::Stdout(format!("Failed to spawn: {}", e))).await;
            return;
        }
    };

    let stdout = child.stdout.take().expect("Failed to open stdout");
    let stderr = child.stderr.take().expect("Failed to open stderr");
    let mut stdout_reader = BufReader::new(stdout).lines();
    let mut stderr_reader = BufReader::new(stderr).lines();

    let tx_clone1 = tx.clone();
    let parser1 = crate::parser::Parser::new();
    tokio::spawn(async move {
        while let Ok(Some(line)) = stdout_reader.next_line().await {
            for event in parser1.parse_line(&line) {
                let _ = tx_clone1.send(event).await;
            }
            if tx_clone1.send(LogEvent::Stdout(line)).await.is_err() {
                break;
            }
        }
    });

    let tx_clone2 = tx.clone();
    let parser2 = crate::parser::Parser::new();
    tokio::spawn(async move {
        while let Ok(Some(line)) = stderr_reader.next_line().await {
            for event in parser2.parse_line(&line) {
                let _ = tx_clone2.send(event).await;
            }
            if tx_clone2.send(LogEvent::Stdout(line)).await.is_err() {
                break;
            }
        }
    });

    tokio::select! {
        _ = kill_rx.recv() => {
            let _ = child.kill().await;
            let _ = tx.send(LogEvent::ProcessExit(())).await;
        }
        _ = child.wait() => {
            let _ = tx.send(LogEvent::ProcessExit(())).await;
        }
    }
}
