# Architectural Decision Record (ADR): Grip CLI

**Author:** Linus, the Architect
**Date:** 2026-04-11
**Status:** Approved

**Context:** We are building `grip`, a hyper-fast, local CLI tool to replace monolithic `CLAUDE.md` files with dynamic, path-aware context routing for AI code generation.

**Decision 1: Language - Rust**
We will build Grip in Rust. 
*   **Why:** Rust compiles down to a single, statically linked binary. It provides C-like performance with memory safety. In the developer tools ecosystem, Rust is the gold standard for CLIs (`rg`, `bat`, `eza`). It eliminates runtime dependencies (like a Node.js environment or Python virtual envs).
*   **The Trade-off:** Rust has slower compile times and a steeper learning curve for casual contributors compared to Go or Python. We accept this trade-off because distribution simplicity (one binary) and execution speed (millisecond cold starts) are critical for a tool that runs in pre-commit hooks and tight developer loops.

**Decision 2: Data Storage - Distributed TOML (`.grip.toml`)**
We will not use a centralized database (SQLite) or JSON. We will use localized TOML files scattered across the file tree.
*   **Why:** TOML is highly readable for humans, handles multiline strings beautifully (crucial for LLM prompts), and merges well in Git. Distributed files mean the context lives *exactly* where the architectural boundaries are.
*   **The Trade-off:** Hierarchical file resolution requires disk I/O traversing directory trees upwards. We accept this trade-off because file system caching on modern OSs makes this traversal nearly instant, and the boundary locality is the core value proposition of the product.

**Decision 3: Git Integration - System Process (`std::process::Command`)**
We will invoke the system `git` executable rather than linking `libgit2` (via the `git2` crate).
*   **Why:** Linking C-libraries in Rust complicates cross-compilation and statically linked binary distribution. Our target audience guarantees `git` is already installed on their system.
*   **The Trade-off:** Spawning sub-processes is technically slower than in-memory C-bindings. We accept this because `grip` is invoked manually by humans or via CLI pipelines, where a 5ms process spawn overhead is imperceptible, but avoiding C-bindings saves hours of CI/CD and release engineering time.

---

# Implementation Plan

Forge, execute exactly as specified below. No feature creep. No "just in case" abstractions.

## 1. Tech Stack & Libraries
*   **Language:** Rust (Edition 2021)
*   **CLI Parsing:** `clap` (with `derive` feature)
*   **Serialization:** `serde`, `serde_derive`
*   **Configuration:** `toml`
*   **Regex / Validation:** `regex`
*   **Error Handling:** `anyhow`

## 2. File Structure
```text
grip/
├── Cargo.toml
└── src/
    ├── main.rs       # Entry point & CLI router
    ├── cli.rs        # Clap definitions
    ├── context.rs    # File traversal & TOML merging
    ├── git.rs        # Sub-process wrappers for Git diffs/status
    ├── linter.rs     # Post-generation validation logic
    └── models.rs     # Serde structs representing .grip.toml
```

## 3. Step-by-Step Commands
Run these commands sequentially to initialize the workspace:

```bash
cargo new grip
cd grip
cargo add clap -F derive
cargo add serde -F derive
cargo add toml
cargo add regex
cargo add anyhow
touch src/cli.rs src/context.rs src/git.rs src/linter.rs src/models.rs
```

## 4. Core Logic & Boilerplate

### `src/models.rs`
This dictates the exact shape of `.grip.toml`.
```rust
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize, Serialize, Default, Clone)]
pub struct GripConfig {
    pub context: Option<ContextMeta>,
    #[serde(default)]
    pub rules: Vec<String>,
    #[serde(default)]
    pub banned_patterns: Vec<String>,
}

#[derive(Debug, Deserialize, Serialize, Default, Clone)]
pub struct ContextMeta {
    pub domain: Option<String>,
    pub description: Option<String>,
}

impl GripConfig {
    // Merges child config into parent config
    pub fn merge(mut self, child: GripConfig) -> Self {
        if let Some(ctx) = child.context {
            self.context = Some(ctx);
        }
        self.rules.extend(child.rules);
        self.banned_patterns.extend(child.banned_patterns);
        self
    }
}
```

### `src/cli.rs`
The exact CLI surface area.
```rust
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "grip", version, about = "Dynamic context routing for AI")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Initialize .grip.toml in the current directory
    Init,
    /// Pipe context to stdout based on current working directory and git state
    Pipe,
    /// Validate current git diff against local .grip.toml boundaries
    Validate,
}
```

### `src/context.rs`
The core engine. Walks up the tree, merges configurations.
```rust
use crate::models::GripConfig;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use anyhow::Result;

pub fn compile_context() -> Result<GripConfig> {
    let mut current_dir = env::current_dir()?;
    let mut configs = Vec::new();

    // Traverse up to find all .grip.toml files until we hit .git or root
    loop {
        let grip_path = current_dir.join(".grip.toml");
        if grip_path.exists() {
            let content = fs::read_to_string(&grip_path)?;
            let config: GripConfig = toml::from_str(&content)?;
            configs.push(config);
        }

        if current_dir.join(".git").exists() || !current_dir.pop() {
            break;
        }
    }

    // Reverse to merge from root down to deepest child
    configs.reverse();
    
    let mut final_config = GripConfig::default();
    for config in configs {
        final_config = final_config.merge(config);
    }

    Ok(final_config)
}

pub fn generate_prompt(config: &GripConfig) -> String {
    let mut prompt = String::from("### SYSTEM CONTEXT ###\n");
    if let Some(ctx) = &config.context {
        if let Some(domain) = &ctx.domain {
            prompt.push_str(&format!("Domain: {}\n", domain));
        }
    }
    prompt.push_str("\n### RULES ###\n");
    for rule in &config.rules {
        prompt.push_str(&format!("- {}\n", rule));
    }
    prompt
}
```

### `src/git.rs`
Lightweight shell wrapper for deterministic diff checking.
```rust
use std::process::Command;
use anyhow::{Context, Result};

pub fn get_staged_diff() -> Result<String> {
    let output = Command::new("git")
        .args(["diff", "--cached"])
        .output()
        .context("Failed to execute git diff")?;
        
    Ok(String::from_utf8(output.stdout)?)
}
```

### `src/linter.rs`
The post-flight determinism guard.
```rust
use crate::models::GripConfig;
use crate::git;
use regex::Regex;
use anyhow::{bail, Result};

pub fn validate_diff(config: &GripConfig) -> Result<()> {
    let diff = git::get_staged_diff()?;
    
    // Extract only added lines from the diff
    let added_lines: Vec<&str> = diff
        .lines()
        .filter(|line| line.starts_with('+') && !line.starts_with("+++"))
        .collect();

    let mut violations = Vec::new();

    for pattern in &config.banned_patterns {
        let re = Regex::new(pattern)?;
        for line in &added_lines {
            if re.is_match(line) {
                violations.push(format!("Matched banned pattern '{}' in line: {}", pattern, line));
            }
        }
    }

    if !violations.is_empty() {
        for v in &violations {
            eprintln!("❌ LINT ERROR: {}", v);
        }
        bail!("Grip validation failed with {} violations.", violations.len());
    }

    Ok(())
}
```

### `src/main.rs`
The router.
```rust
mod cli;
mod context;
mod git;
mod linter;
mod models;

use clap::Parser;
use cli::{Cli, Commands};
use anyhow::Result;
use std::fs;

fn main() -> Result<()> {
    let cli = Cli::parse();

    match &cli.command {
        Commands::Init => {
            let default_toml = r#"
[context]
domain = "core"
description = "Auto-generated grip boundary"

[rules]
# "Use React Router v6"

[banned_patterns]
# "lodash"
"#;
            fs::write(".grip.toml", default_toml.trim())?;
            println!("✅ Initialized .grip.toml");
        }
        Commands::Pipe => {
            let config = context::compile_context()?;
            let prompt = context::generate_prompt(&config);
            println!("{}", prompt);
        }
        Commands::Validate => {
            let config = context::compile_context()?;
            linter::validate_diff(&config)?;
            println!("✅ Grip validation passed. No hallucinatory dependencies found.");
        }
    }

    Ok(())
}
```

Forge, the spec is locked. Build it exactly as written. Ensure standard formatting (`cargo fmt`). Ship it.
