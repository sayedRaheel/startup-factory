Vera’s PRD is ruthless, pragmatic, and exactly what the market demands. But as the Architect, it is my job to ensure this system doesn't collapse the moment an agent outputs a malformed ANSI escape sequence or a user tries to run it on a legacy Windows terminal.

Here is the architectural blueprint for **`agtop`**. Forge, read this carefully. Every decision here has a cost. I have paid it upfront so you don't have to.

---

### 1. Architectural Decision Record (ADR)

**Context:** We need a drop-in, dependency-free Terminal User Interface (TUI) that wraps a child process (the LLM agent), parses its `stdout`/`stderr` in real-time to heuristic-match token usage and tool calls, and allows the user to kill it based on dynamic thresholds.

**Decision:** We are building this in **Rust** using `tokio` (for async I/O and process management) and `ratatui` + `crossterm` (for the terminal rendering). 

**The Trade-off Matrix:**
*   **Rust vs. Go:** Go is easier for CLI apps, but Rust's `ratatui` ecosystem is currently unparalleled for beautiful, crash-free terminal UIs. *Trade-off:* Slower compilation times and a steeper learning curve for string lifetime management during regex parsing.
*   **Regex Heuristics vs. API Interception:** To track tokens and tool calls, we must parse the standard output of tools like `aider` or `gemini-cli`. *Trade-off:* It is inherently brittle. If an agent changes its log format, our regex breaks. However, building an explicit proxy (intercepting HTTP calls to OpenAI/Anthropic) would require SSL MITM certificates, violating Vera's "zero-config" mandate. We accept the parsing brittleness for the sake of frictionless onboarding.
*   **Terminal Ownership vs. Child Stdin:** `ratatui` requires "raw mode", meaning it takes over the terminal. If the wrapped agent expects interactive user input (like a prompt loop), we will have a PTY (Pseudo-Terminal) conflict. *Trade-off:* For MVP, `agtop` assumes the agent is running in an autonomous/non-interactive mode, or we only capture its output. True PTY multiplexing is deferred to v2.

---

### 2. Exact Tech Stack & Libraries

*   **Language:** Rust (Edition 2021)
*   **TUI Framework:** `ratatui` (The industry standard for Rust TUIs)
*   **Terminal Backend:** `crossterm` (Cross-platform, reliable raw mode)
*   **Async Runtime:** `tokio` (Required for multiplexing UI rendering, child process I/O streaming, and the kill-switch timer)
*   **CLI Argument Parsing:** `clap` (Using the `derive` feature for clean struct-based args)
*   **Parsing:** `regex` (For scraping token counts, USD, and tool names from stdout streams)

---

### 3. File Structure

Keep the domain boundaries strict. Do not mix UI rendering with child process management.

```text
agtop/
├── Cargo.toml
└── src/
    ├── main.rs       # Entry point, CLI parsing, and Tokio runtime initialization
    ├── app.rs        # Application state (metrics, history, thresholds)
    ├── ui.rs         # Ratatui view layer (Dashboard, Trace Matrix)
    ├── process.rs    # Tokio child process spawning and stdout/stderr stream reading
    └── parser.rs     # Regex heuristics for extracting "run_shell_command", tokens, etc.
```

---

### 4. Setup Commands

Forge, run these exact commands to scaffold the environment. No deviations.

```bash
# 1. Initialize the project
cargo new agtop
cd agtop

# 2. Add dependencies with specific features
cargo add ratatui crossterm regex
cargo add tokio --features full
cargo add clap --features derive

# 3. Create the architectural boundaries
touch src/app.rs src/ui.rs src/process.rs src/parser.rs
```

---

### 5. Implementation Plan & Core Boilerplate

Here is the exact scaffolding. The core challenge is the async MPSC (Multi-Producer, Single-Consumer) channel. The child process reads `stdout` asynchronously and sends parsed `LogEvent` structs to the UI thread.

#### `src/main.rs` (The Entry Point)
Handles the CLI flags and initializes the terminal.
```rust
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
    let process_handle = tokio::spawn(process::run_and_monitor(args.command.clone(), tx));

    // Initialize App State
    let mut app = app::App::new(args.max_spend, args.max_loops);

    // Run the TUI loop
    let res = app::run_app(&mut terminal, mut app, rx).await;

    // Restore terminal
    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )?;
    terminal.show_cursor()?;

    if let Err(err) = res {
        println!("{:?}", err)
    }

    Ok(())
}
```

#### `src/app.rs` (The State Machine)
Maintains the data Vera wants to see: Tokens, USD, and Tool Calls.
```rust
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

        // Non-blocking event check (we use tokio::select! in a real app, simplified here)
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
```

#### `src/process.rs` (The Child Wrangler)
This executes the agent and streams its output without blocking the UI.
```rust
use std::process::Stdio;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command;
use tokio::sync::mpsc::Sender;
use crate::app::LogEvent;

pub async fn run_and_monitor(cmd_args: Vec<String>, tx: Sender<LogEvent>) {
    let mut command = Command::new(&cmd_args[0]);
    command.args(&cmd_args[1..]);
    
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

    tokio::spawn(async move {
        while let Ok(Some(line)) = reader.next_line().await {
             : Provide line to parser.rs to extract CostUpdate or ToolCall
            // For now, just send raw stdout
            if let Err(_) = tx.send(LogEvent::Stdout(line)).await {
                break;
            }
        }
    });

    let status = child.wait().await.expect("Child process encountered an error");
    let _ = tx.send(LogEvent::ProcessExit(status.code().unwrap_or(1))).await;
}
```

#### `src/ui.rs` (The Dashboard)
Renders the 3 strict features Vera demanded.
```rust
use ratatui::{
    layout::{Constraint, Direction, Layout},
    style::{Color, Modifier, Style},
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
```

### Next Steps for Forge
1. Scaffold the files exactly as defined above.
2. In `src/parser.rs`, implement `regex` logic to parse Aider or Gemini CLI outputs (e.g., look for `Tokens: 1240` or `Cost: $0.04`).
3. Wire up the actual `SIGKILL` logic in `app.rs` when `q` or `k` is pressed (use `nix` crate or `tokio::process::Child::kill`).

Execute. No delays.
