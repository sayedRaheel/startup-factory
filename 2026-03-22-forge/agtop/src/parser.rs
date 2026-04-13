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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parser() {
        let parser = Parser::new();
        let evs = parser.parse_line("Total cost: $4.50 today");
        assert_eq!(evs.len(), 1);
        if let LogEvent::CostUpdate(c) = evs[0] {
            assert_eq!(c, 4.5);
        } else {
            panic!("Expected CostUpdate");
        }
        
        let evs2 = parser.parse_line("Action: tool call run_shell_command detected");
        assert_eq!(evs2.len(), 1);
        if let LogEvent::ToolCall(ref t) = evs2[0] {
            assert_eq!(t, "run_shell_command");
        } else {
            panic!("Expected ToolCall");
        }
    }
}
