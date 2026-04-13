#!/bin/bash
set -euo pipefail

source "$HOME/.cargo/env" || true

rm -rf agtop
cargo new agtop
cd agtop

cargo add ratatui crossterm regex
cargo add tokio --features full
cargo add clap --features derive

cat << 'RUST' > src/main.rs
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
    #[arg(long)]
    max_spend: Option<f64>,

    #[arg(long)]
    max_loops: Option<usize>,

    #[arg(last = true, required = true)]
    command: Vec<String>,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let args = Args::parse();

    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    let (tx, rx) = mpsc::channel(100);
    let (kill_tx, kill_rx) = mpsc::channel::<()>(1);

    let _process_handle = tokio::spawn(process::run_and_monitor(args.command.clone(), tx, kill_rx));

    let app = app::App::new(args.max_spend, args.max_loops);

    let res = app::run_app(&mut terminal, app, rx, kill_tx).await;

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
RUST

cat << 'RUST' > src/app.rs
use crossterm::event::{self, Event, KeyCode};
use ratatui::{backend::Backend, Terminal};
use tokio::sync::mpsc::{Receiver, Sender};

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
        if let Some(limit) = self.max_loops {
            if self.tool_traces.len() >= limit {
                return true;
            }
        }
        false
    }
}

pub async fn run_app<B: Backend>(
    terminal: &mut Terminal<B>,
    mut app: App,
    mut rx: Receiver<LogEvent>,
    kill_tx: Sender<()>,
) -> std::io::Result<()> {
    loop {
        terminal.draw(|f| crate::ui::ui(f, &app))?;

        if event::poll(std::time::Duration::from_millis(50))? {
            if let Event::Key(key) = event::read()? {
                match key.code {
                    KeyCode::Char('q') | KeyCode::Char('k') => {
                        app.should_quit = true;
                        let _ = kill_tx.send(()).await;
                    }
                    _ => {}
                }
            }
        }

        while let Ok(event) = rx.try_recv() {
            match event {
                LogEvent::Stdout(line) => {
                    app.raw_logs.push(line);
                    if app.raw_logs.len() > 100 {
                        app.raw_logs.remove(0);
                    }
                }
                LogEvent::ToolCall(tool) => app.tool_traces.push(tool),
                LogEvent::CostUpdate(cost) => app.current_cost += cost,
                LogEvent::ProcessExit(_) => app.should_quit = true,
            }
        }

        if !app.should_quit && app.check_guillotine() {
            let _ = kill_tx.send(()).await;
            app.should_quit = true;
        }

        if app.should_quit {
            return Ok(());
        }
    }
}
RUST

cat << 'RUST' > src/process.rs
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
            let _ = tx.send(LogEvent::ProcessExit(137)).await;
        }
        status = child.wait() => {
            let code = status.expect("Child process encountered an error").code().unwrap_or(1);
            let _ = tx.send(LogEvent::ProcessExit(code)).await;
        }
    }
}
RUST

cat << 'RUST' > src/ui.rs
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
                Constraint::Length(3),
                Constraint::Min(1),
            ]
            .as_ref(),
        )
        .split(f.size());

    let cost_style = if let Some(max) = app.max_spend {
        if app.current_cost > max * 0.8 { Style::default().fg(Color::Red) } else { Style::default().fg(Color::Green) }
    } else {
        Style::default().fg(Color::Green)
    };

    let dashboard = Paragraph::new(format!(
        " 💰 Cost: ${:.4} | 🛑 Guillotine: {} | 🔄 Trace Tools: {}",
        app.current_cost,
        app.max_spend.map(|m| format!("${:.2}", m)).unwrap_or_else(|| "OFF".to_string()),
        app.tool_traces.len()
    ))
    .block(Block::default().borders(Borders::ALL).title(" Live Burn Dashboard "))
    .style(cost_style);
    f.render_widget(dashboard, chunks[0]);

    let logs: Vec<ListItem> = app
        .raw_logs
        .iter()
        .rev()
        .take(50)
        .map(|m| ListItem::new(m.as_str()))
        .collect();

    let trace_matrix = List::new(logs)
        .block(Block::default().borders(Borders::ALL).title(" Tool-Call Trace Matrix (Press 'k' to KILL) "));
    f.render_widget(trace_matrix, chunks[1]);
}
RUST

cat << 'RUST' > src/parser.rs
use regex::Regex;
use crate::app::LogEvent;

pub struct Parser {
    pub cost_regex: Regex,
    pub tool_regex: Regex,
}

impl Parser {
    pub fn new() -> Self {
        Self {
            cost_regex: Regex::new(r"(?i)(?:cost|spend|price).*?\$([0-9]+(?:\.[0-9]+)?)").unwrap(),
            tool_regex: Regex::new(r"(?i)(?:tool|call|function|cmd).*?(run_shell_command|read_file|write_file|grep_search|replace|glob|web_fetch)").unwrap(),
        }
    }

    pub fn parse_line(&self, line: &str) -> Vec<LogEvent> {
        let mut events = Vec::new();
        if let Some(caps) = self.cost_regex.captures(line) {
            if let Ok(val) = caps[1].parse::<f64>() {
                events.push(LogEvent::CostUpdate(val));
            }
        }
        if let Some(caps) = self.tool_regex.captures(line) {
            events.push(LogEvent::ToolCall(caps[1].to_string()));
        }
        events
    }
}
RUST

cargo check
cargo build

