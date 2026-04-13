use clap::{Parser, Subcommand};
use ignore::WalkBuilder;
use reqwest::header::{AUTHORIZATION, CONTENT_TYPE};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Parser)]
#[command(name = "vise")]
#[command(about = "The .editorconfig for Agentic Determinism", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,

    /// The prompt to execute
    prompt: Option<String>,
}

#[derive(Subcommand)]
enum Commands {
    /// Initialize aivise constraints
    Init,
}

#[derive(Serialize, Deserialize, Debug)]
struct AiviseConfig {
    language: String,
    lint_command: String,
    strict_rules: Vec<String>,
}

impl Default for AiviseConfig {
    fn default() -> Self {
        Self {
            language: "rust".to_string(),
            lint_command: "cargo check".to_string(),
            strict_rules: vec![
                "Never use panic().".to_string(),
                "Always add inline documentation for public functions.".to_string(),
            ],
        }
    }
}

#[derive(Serialize, Deserialize, Debug)]
struct FileChange {
    path: String,
    content: String,
}

#[derive(Serialize, Deserialize, Debug)]
struct AiResponse {
    files: Vec<FileChange>,
}

#[tokio::main]
async fn main() {
    let cli = Cli::parse();

    match cli.command {
        Some(Commands::Init) => {
            init_aivise();
            println!("✔ Generated .aivise configuration.");
            return;
        }
        None => {
            if let Some(prompt) = cli.prompt {
                run_prompt(prompt).await;
            } else {
                println!("Usage: vise <prompt> | vise init");
                std::process::exit(1);
            }
        }
    }
}

fn init_aivise() {
    let config = AiviseConfig::default();
    let toml_string = toml::to_string(&config).unwrap();
    fs::write(".aivise", toml_string).unwrap();
}

fn load_aivise() -> AiviseConfig {
    if let Ok(content) = fs::read_to_string(".aivise") {
        toml::from_str(&content).unwrap_or_default()
    } else {
        AiviseConfig::default()
    }
}

fn compile_context() -> String {
    let mut context = String::new();
    let walker = WalkBuilder::new(".").hidden(false).build();
    for entry in walker.flatten() {
        let path = entry.path();
        if path.is_file() {
            let p_str = path.to_string_lossy();
            if p_str.contains(".git/") || p_str.contains("target/") || p_str.contains("node_modules/") {
                continue;
            }
            if let Ok(content) = fs::read_to_string(path) {
                context.push_str(&format!("--- FILE: {} ---\n{}\n", p_str, content));
            }
        }
    }
    context
}

async fn execute_prompt(prompt: &str, context: &str, config: &AiviseConfig) -> AiResponse {
    let api_key = env::var("OPENAI_API_KEY").unwrap_or_default();
    if api_key.is_empty() {
        println!("Warning: OPENAI_API_KEY not set. Returning a deterministic mock response.");
        return AiResponse { files: vec![] };
    }

    let rules = config.strict_rules.join(" ");
    let system_prompt = format!(
        "You are an infallible code compiler. Rules: {}. Context: {}. OUTPUT STRICTLY JSON. NO MARKDOWN. NO CHAT. Format: {{ \"files\": [ {{ \"path\": \"str\", \"content\": \"str\" }} ] }}",
        rules, context
    );

    let client = reqwest::Client::new();
    let body = serde_json::json!({
        "model": "gpt-4o",
        "response_format": { "type": "json_object" },
        "messages": [
            { "role": "system", "content": system_prompt },
            { "role": "user", "content": prompt }
        ]
    });

    let res = client
        .post("https://api.openai.com/v1/chat/completions")
        .header(AUTHORIZATION, format!("Bearer {}", api_key))
        .header(CONTENT_TYPE, "application/json")
        .json(&body)
        .send()
        .await
        .unwrap();

    let json_res: serde_json::Value = res.json().await.unwrap();
    let content = json_res["choices"][0]["message"]["content"].as_str().unwrap();
    serde_json::from_str(content).unwrap()
}

fn apply_diff(response: &AiResponse) -> HashMap<PathBuf, Option<String>> {
    let mut backup = HashMap::new();
    for file in &response.files {
        let path = Path::new(&file.path);
        if path.exists() {
            backup.insert(path.to_path_buf(), Some(fs::read_to_string(path).unwrap()));
        } else {
            backup.insert(path.to_path_buf(), None);
        }
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).unwrap();
        }
        fs::write(path, &file.content).unwrap();
    }
    backup
}

fn rollback(backup: HashMap<PathBuf, Option<String>>) {
    for (path, content) in backup {
        if let Some(c) = content {
            fs::write(path, c).unwrap();
        } else {
            let _ = fs::remove_file(path);
        }
    }
}

async fn run_prompt(prompt: String) {
    let config = load_aivise();
    let context = compile_context();
    println!("Compiling context and generating diff...");
    let response = execute_prompt(&prompt, &context, &config).await;
    println!("Applying diff to memory and linting...");
    let backup = apply_diff(&response);

    let mut parts = config.lint_command.split_whitespace();
    if let Some(cmd) = parts.next() {
        let status = Command::new(cmd)
            .args(parts)
            .status()
            .unwrap_or_else(|_| panic!("Failed to execute lint command: {}", config.lint_command));

        if status.success() {
            println!("✔ Lint passed. Changes committed.");
        } else {
            println!("✖ Lint failed. AI hallucinated. Rolling back changes.");
            rollback(backup);
            std::process::exit(1);
        }
    }
}
