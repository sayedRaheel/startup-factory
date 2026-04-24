use regex::Regex;
use serde_json::{json, Value};
use std::io::{self, BufRead, Write};
use std::process::Command;
use std::collections::HashSet;
use std::fs;

struct Engine {
    ansi_regex: Regex,
}

impl Engine {
    fn new() -> Self {
        Engine {
            ansi_regex: Regex::new(r"\x1b\[[0-9;]*m").unwrap(),
        }
    }

    fn process(&self, raw: &str, max_lines: usize) -> String {
        let clean = self.ansi_regex.replace_all(raw, "");
        let lines: Vec<&str> = clean.split('\n').collect();

        if lines.len() <= max_lines {
            return clean.into_owned();
        }

        let top_count = (max_lines as f64 * 0.2).floor() as usize;
        let bottom_count = max_lines - top_count;
        let omitted = lines.len() - max_lines;

        let top_lines = lines[..top_count].join("\n");
        let bottom_lines = lines[lines.len() - bottom_count..].join("\n");

        format!("{}\n\n... [SQUELCHED {} LINES] ...\n\n{}", top_lines, omitted, bottom_lines)
    }
}

struct Vault {
    redaction_regex: Option<Regex>,
}

impl Vault {
    fn new() -> Self {
        let mut secrets = HashSet::new();

        // 1. Harvest from current .env
        if let Ok(env_file) = fs::read_to_string(".env") {
            for line in env_file.lines() {
                if let Some((_key, val)) = line.split_once('=') {
                    let trimmed = val.trim();
                    // Do not redact short strings to avoid corrupting standard text
                    if trimmed.len() >= 6 {
                        secrets.insert(regex::escape(trimmed));
                    }
                }
            }
        }

        // 2. Add standard entropy patterns
        secrets.insert("AKIA[0-9A-Z]{16}".to_string());
        secrets.insert("eyJh[a-zA-Z0-9\\-_]+\\.[a-zA-Z0-9\\-_]+\\.[a-zA-Z0-9\\-_]+".to_string());
        secrets.insert("npm_[a-zA-Z0-9]{36}".to_string());

        let redaction_regex = if secrets.is_empty() {
            None
        } else {
            let pattern = secrets.into_iter().collect::<Vec<_>>().join("|");
            Regex::new(&format!("({})", pattern)).ok()
        };

        Vault { redaction_regex }
    }

    fn redact(&self, input: &str) -> String {
        if let Some(re) = &self.redaction_regex {
            re.replace_all(input, "[REDACTED_SECRET]").to_string()
        } else {
            input.to_string()
        }
    }
}

fn create_response(id: Option<Value>, result: Option<Value>, error: Option<Value>) -> Value {
    let mut res = json!({
        "jsonrpc": "2.0",
        "id": id.unwrap_or(Value::Null)
    });

    if let Some(err) = error {
        res.as_object_mut().unwrap().insert("error".to_string(), err);
    } else if let Some(res_val) = result {
        res.as_object_mut().unwrap().insert("result".to_string(), res_val);
    }

    res
}

fn main() {
    eprintln!("Squelch MCP Server initialized.");

    let vault = Vault::new();
    let engine = Engine::new();

    let stdin = io::stdin();
    let mut stdout = io::stdout();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => continue,
        };

        if line.trim().is_empty() {
            continue;
        }

        let req: Value = match serde_json::from_str(&line) {
            Ok(val) => val,
            Err(e) => {
                eprintln!("Parse error: {}", e);
                continue;
            }
        };

        let id = req.get("id").cloned();
        let method = req.get("method").and_then(|m| m.as_str()).unwrap_or("");

        if method == "initialize" {
            let res = create_response(
                id,
                Some(json!({
                    "protocolVersion": "2024-11-05",
                    "capabilities": { "tools": {} },
                    "serverInfo": { "name": "squelch", "version": "1.0.0" }
                })),
                None,
            );
            writeln!(stdout, "{}", res.to_string()).unwrap();
        } else if method == "tools/list" {
            let res = create_response(
                id,
                Some(json!({
                    "tools": [{
                        "name": "squelched_shell",
                        "description": "Execute a shell command with smart truncation and secret redaction.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "command": { "type": "string" }
                            },
                            "required": ["command"]
                        }
                    }]
                })),
                None,
            );
            writeln!(stdout, "{}", res.to_string()).unwrap();
        } else if method == "tools/call" {
            let params = req.get("params");
            let name = params.and_then(|p| p.get("name")).and_then(|n| n.as_str());

            if name == Some("squelched_shell") {
                let cmd_str = params
                    .and_then(|p| p.get("arguments"))
                    .and_then(|a| a.get("command"))
                    .and_then(|c| c.as_str())
                    .unwrap_or("");

                let output = Command::new("sh")
                    .arg("-c")
                    .arg(cmd_str)
                    .output();

                let (raw_out, raw_err) = match output {
                    Ok(out) => (
                        String::from_utf8_lossy(&out.stdout).to_string(),
                        String::from_utf8_lossy(&out.stderr).to_string(),
                    ),
                    Err(e) => ("".to_string(), e.to_string()),
                };

                let combined = format!("STDOUT:\n{}\nSTDERR:\n{}", raw_out, raw_err);
                let processed = engine.process(&combined, 100);
                let sanitized = vault.redact(&processed);

                let res = create_response(
                    id,
                    Some(json!({
                        "content": [{
                            "type": "text",
                            "text": sanitized
                        }]
                    })),
                    None,
                );

                writeln!(stdout, "{}", res.to_string()).unwrap();
            } else {
                let res = create_response(
                    id,
                    None,
                    Some(json!({ "code": -32601, "message": "Method not found" })),
                );
                writeln!(stdout, "{}", res.to_string()).unwrap();
            }
        } else {
            let res = create_response(
                id,
                None,
                Some(json!({ "code": -32601, "message": "Method not found" })),
            );
            writeln!(stdout, "{}", res.to_string()).unwrap();
        }
        stdout.flush().unwrap();
    }
}
