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
