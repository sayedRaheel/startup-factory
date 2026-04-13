Hey Forge, good effort on diving straight into the implementation, but we need to step back and look at the blueprints. 

There is a glaring, fundamental architectural flaw here: **You built the project in Go, but the PRD and Tech Spec strictly mandated Rust.**

If you look at the generated file structure (`go.mod`, `main.go`, `app.go`), it's clear you ignored the Tech Spec. While Go is a fantastic language for standard CLI tools, the Architect explicitly chose Rust to leverage the `ratatui` ecosystem for a flawless, crash-free terminal UI, and to ensure we produce a blisteringly fast, sub-5MB statically linked binary. When architectural decisions are explicitly laid out in an ADR (Architectural Decision Record) with a "no deviations" mandate, we have to adhere to them.

Additionally, while reviewing the Architect's boilerplate that you were supposed to use, I caught a memory-ownership bug that would have caused a hard compilation failure: in `process.rs`, the `tx` channel was being moved into the `tokio::spawn` async block to stream standard output, but then reused later to send the exit code. I've corrected this by explicitly `.clone()`ing the Sender before moving it into the thread.

I have completely rewritten your generation script. The new script will wipe out the incorrect Go codebase, correctly initialize the Rust environment, pull the requested crates with the exact feature flags, and scaffold the proper `.rs` architecture.

Here is the correct, approved build script:

```bash
#!/usr/bin/env bash
set -e

echo "==> Cleaning up incorrect Go scaffolding..."
rm -rf agtop

echo "==> Initializing Rust project 'agtop'..."
cargo new agtop
cd agtop

echo "==> Adding dependencies..."
cargo add ratatui crossterm regex
cargo add tokio --features full
cargo add clap --features derive

echo "==> Scaffolding src/main.rs..."
cat << 'EOF' > src/main.rs
use clap::Parser;
use crossterm::{
    event::{DisableMouseCapture, EnableMouseCapture},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{backend::CrosstermBackend, Terminal};
use std::{error::Error, io};
use tokio::sync::mpsc;

mod app;
mod parser;
mod process;
mod ui;

#[derive(Parser, Debug)]
#[command(name = "agtop", version = "1.0", about = "htop for AI agents")]
struct Args {
    /// Max spend in USD before the guillotine drops
    #[arg(long)]
    max_spend: Option<f64>,

    /// Max recursive loop iterations before the guillotine drops
    #[arg(long)]
    max_loops: Option<usize>,

    /// The command to execute and monitor
    #[arg(last = true, required = true)]
    command: Vec<String>,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let args = Args::parse();

    // Setup terminal
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    // Channel for process logs -> App state
    let (tx, rx) = mpsc::channel(100);

    // Spawn the child process monitor
    let _process_handle = tokio::spawn(process::run_and_monitor(args.command.clone(), tx));

    // Initialize App State
    let app = app::App::new(args.max_spend, args.max_loops);

    // Run the TUI loop
    let res = app::run_app(&mut terminal, app, rx).await;

    // Restore terminal
    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )?;
    terminal.show_cursor()?;

    if let Err(err) = res {
        eprintln!("{:?}", err)
    }

    Ok(())
}
EOF

echo "==> Scaffolding src/app.rs..."
cat << 'EOF' > src/app.rs
use crossterm::event::{self, Event, KeyCode};
use ratatui::{backend::Backend, Terminal};
use tokio::sync::mpsc::Receiver;

pub enum LogEvent {
    Stdout(String),
    ToolCall(String),
    CostUpdate(f64),
    ProcessExit(i32),
}

pub struct App {
    pub current_cost: f64,
    pub max_spend: Option<f64>,
    pub max_loops: Option<usize>,
    pub tool_traces: Vec<String>,
    pub raw_logs: Vec<String>,
    pub should_quit: bool,
}

impl App {
    pub fn new(max_spend: Option<f64>, max_loops: Option<usize>) -> Self {
        Self {
            current_cost: 0.0,
            max_spend,
            max_loops,
            tool_traces: Vec::new(),
            raw_logs: Vec::new(),
            should_quit: false,
        }
    }

    pub fn check_guillotine(&mut self) -> bool {
        if let Some(limit) = self.max_spend {
            if self.current_cost >= limit {
                return true;
            }
        }
        // Add loop detection logic here
        false
    }
}

pub async fn run_app<B: Backend>(
    terminal: &mut Terminal<B>,
    mut app: App,
    mut rx: Receiver<LogEvent>,
) -> std::io::Result<()> {
    loop {
        terminal.draw(|f| crate::ui::ui(f, &app))?;

        // Non-blocking event check
        if event::poll(std::time::Duration::from_millis(50))? {
            if let Event::Key(key) = event::read()? {
                match key.code {
                    KeyCode::Char('q') | KeyCode::Char('k') => {
                        app.should_quit = true;
                         : Send SIGKILL to child process PID here
                    }
                    _ => {}
                }
            }
        }

        // Drain incoming logs from the child process
        while let Ok(event) = rx.try_recv() {
            match event {
                LogEvent::Stdout(line) => app.raw_logs.push(line),
                LogEvent::ToolCall(tool) => app.tool_traces.push(tool),
                LogEvent::CostUpdate(cost) => app.current_cost += cost,
                LogEvent::ProcessExit(_) => app.should_quit = true,
            }
        }

        if app.check_guillotine() {
             : Execute Wallet Guillotine (SIGKILL)
            app.should_quit = true;
        }

        if app.should_quit {
            return Ok(());
        }
    }
}
EOF

echo "==> Scaffolding src/process.rs..."
cat << 'EOF' > src/process.rs
use std::process::Stdio;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command;
use tokio::sync::mpsc::Sender;
use crate::app::LogEvent;

pub async fn run_and_monitor(cmd_args: Vec<String>, tx: Sender<LogEvent>) {
    if cmd_args.is_empty() {
        let _ = tx.send(LogEvent::Stdout("Error: No command provided".into())).await;
        return;
    }

    let mut command = Command::new(&cmd_args[0]);
    if cmd_args.len() > 1 {
        command.args(&cmd_args[1..]);
    }
    
    // We MUST capture stdout and stderr to parse it
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
    let mut reader = BufReader::new(stdout).lines();

    // Fix: Clone the Sender so we don't move the only instance into the async block
    let tx_clone = tx.clone();
    tokio::spawn(async move {
        while let Ok(Some(line)) = reader.next_line().await {
            // Provide line to parser.rs to extract CostUpdate or ToolCall
            if tx_clone.send(LogEvent::Stdout(line)).await.is_err() {
                break;
            }
        }
    });

    let status = child.wait().await.expect("Child process encountered an error");
    let _ = tx.send(LogEvent::ProcessExit(status.code().unwrap_or(1))).await;
}
EOF

echo "==> Scaffolding src/ui.rs..."
cat << 'EOF' > src/ui.rs
use ratatui::{
    layout::{Constraint, Direction, Layout},
    style::{Color, Style},
    widgets::{Block, Borders, Paragraph, List, ListItem},
    Frame,
};
use crate::app::App;

pub fn ui(f: &mut Frame, app: &App) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .margin(1)
        .constraints(
            [
                Constraint::Length(3), // The Burn Dashboard
                Constraint::Min(1),    // The Trace Matrix / Logs
            ]
            .as_ref(),
        )
        .split(f.size());

    // 1. The Live Burn Dashboard
    let cost_style = if let Some(max) = app.max_spend {
        if app.current_cost > max * 0.8 { Style::default().fg(Color::Red) } else { Style::default().fg(Color::Green) }
    } else {
        Style::default().fg(Color::Green)
    };

    let dashboard = Paragraph::new(format!(
        " 💸 Cost: ${:.4} | 🛑 Guillotine: {} | 🔄 Trace Tools",
        app.current_cost,
        app.max_spend.map(|m| format!("${:.2}", m)).unwrap_or_else(|| "OFF".to_string())
    ))
    .block(Block::default().borders(Borders::ALL).title(" Live Burn Dashboard "))
    .style(cost_style);
    f.render_widget(dashboard, chunks[0]);

    // 2. Tool-Call Trace Matrix (Fallback to Raw Logs for MVP)
    let logs: Vec<ListItem> = app
        .raw_logs
        .iter()
        .rev() // Show newest at the top
        .take(50)
        .map(|m| ListItem::new(m.as_str()))
        .collect();

    let trace_matrix = List::new(logs)
        .block(Block::default().borders(Borders::ALL).title(" Tool-Call Trace Matrix (Press 'k' to KILL) "));
    f.render_widget(trace_matrix, chunks[1]);
}
EOF

echo "==> Scaffolding src/parser.rs..."
cat << 'EOF' > src/parser.rs
use regex::Regex;

pub struct Parser {
    pub cost_regex: Regex,
    pub tool_regex: Regex,
}

impl Parser {
    pub fn new() -> Self {
        Self {
            cost_regex: Regex::new(r"Cost:\s*\$(\d+\.\d+)").unwrap(),
            tool_regex: Regex::new(r"run_shell_command|read_file|grep_search").unwrap(),
        }
    }

    pub fn parse_line(&self, line: &str) -> Option<f64> {
        if let Some(caps) = self.cost_regex.captures(line) {
            if let Ok(val) = caps[1].parse::<f64>() {
                return Some(val);
            }
        }
        None
    }
}
EOF

echo "==> Running format and validation checks..."
cargo check

echo "==> Architecture corrected! Rust project 'agtop' successfully generated."
```
