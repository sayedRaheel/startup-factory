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
        .split(f.area());

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
