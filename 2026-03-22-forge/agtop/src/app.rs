use crossterm::event::{self, Event, KeyCode};
use ratatui::Terminal;
use tokio::sync::mpsc::{Receiver, Sender};

#[derive(Debug, Clone, PartialEq)]
pub enum LogEvent {
    Stdout(String),
    ToolCall(String),
    CostUpdate(f64),
    ProcessExit(()),
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

pub async fn run_app(
    terminal: &mut Terminal<ratatui::backend::CrosstermBackend<std::io::Stdout>>,
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_guillotine() {
        let mut app = App::new(Some(1.0), Some(5));
        app.current_cost = 0.5;
        assert!(!app.check_guillotine());
        app.current_cost = 1.05;
        assert!(app.check_guillotine());

        let mut app2 = App::new(None, Some(3));
        app2.tool_traces.push("t1".into());
        app2.tool_traces.push("t2".into());
        assert!(!app2.check_guillotine());
        app2.tool_traces.push("t3".into());
        assert!(app2.check_guillotine());
    }
}
