### Code Review

The Builder's script is **fundamentally flawed** and must be entirely rewritten. 

**Glaring Architectural Flaw:**
The builder completely ignored the core Architectural Decision Record (ADR) mandated by both the PRD and the Tech Spec. The PRD explicitly stated: *"Developers will not install a 500MB Node.js framework just to manage .md files,"* and the Tech Spec required a **Rust** stack to guarantee a single, statically-linked, zero-dependency binary. Instead, the builder ignored these strict constraints and scaffolded a Node.js project using `commander` and `npm install`.

**Why this matters:**
As a developer, you must remember that technology choices are often driven by product constraints and distribution strategy. A zero-dependency binary (`curl | sh`) has a drastically different user experience compared to an application that forces users to install a heavy runtime like Node.js. Ignoring the project's foundational constraints is a critical failure.

I have rewritten the ENTIRE bash script below to align perfectly with the Tech Spec, utilizing Rust, Cargo, `clap`, and `ignore` to build a native binary.

### Corrected Script

```bash
#!/usr/bin/env bash
set -e

echo "Starting Builder script for Tether CLI (Rust)..."

# 1. Scaffold the workspace as requested by the Tech Spec
cargo new tether
cd tether

# Add dependencies
cargo add clap --features derive
cargo add ignore
cargo add serde --features derive
cargo add serde_json

# Create directory structure
mkdir -p src/commands src/detector
touch src/cli.rs src/commands/mod.rs src/commands/init.rs src/commands/map.rs src/detector/mod.rs src/detector/stack.rs

# 2. Write Cargo.toml
cat << 'EOF' > Cargo.toml
[package]
name = "tether-cli"
version = "0.1.0"
edition = "2021"

[dependencies]
clap = { version = "4.4", features = ["derive"] }
ignore = "0.4"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
EOF

# 3. Write Main Entrypoint
cat << 'EOF' > src/main.rs
mod cli;
mod commands;
mod detector;

use clap::Parser;
use cli::{Cli, Commands};

fn main() {
    let cli = Cli::parse();

    let result = match &cli.command {
        Commands::Init => commands::init::execute(),
        Commands::Map => commands::map::execute(),
    };

    if let Err(e) = result {
        eprintln!("Fatal error: {}", e);
        std::process::exit(1);
    }
}
EOF

# 4. Write CLI Parser
cat << 'EOF' > src/cli.rs
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "tether")]
#[command(about = "A lightning-fast CLI to scaffold context boundaries for local AI agents", long_about = None)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Scans the repository and generates standardized .agentrc and SKILLS.md
    Init,
    /// Generates a lightweight, token-optimized architecture graph (.agent-context.md)
    Map,
}
EOF

# 5. Write Detector Module
cat << 'EOF' > src/detector/mod.rs
pub mod stack;
EOF

# 6. Write Stack Heuristics
cat << 'EOF' > src/detector/stack.rs
use std::path::Path;

pub enum Stack {
    Rust,
    Node,
    Python,
    Go,
    Unknown,
}

pub fn detect_stack() -> Stack {
    if Path::new("Cargo.toml").exists() {
        Stack::Rust
    } else if Path::new("package.json").exists() {
        Stack::Node
    } else if Path::new("requirements.txt").exists() || Path::new("pyproject.toml").exists() {
        Stack::Python
    } else if Path::new("go.mod").exists() {
        Stack::Go
    } else {
        Stack::Unknown
    }
}

pub fn stack_name(stack: &Stack) -> &'static str {
    match stack {
        Stack::Rust => "Rust/Cargo",
        Stack::Node => "Node.js",
        Stack::Python => "Python",
        Stack::Go => "Go",
        Stack::Unknown => "Generic/Unknown",
    }
}
EOF

# 7. Write Commands Module
cat << 'EOF' > src/commands/mod.rs
pub mod init;
pub mod map;
EOF

# 8. Write Init Command
cat << 'EOF' > src/commands/init.rs
use std::fs;
use std::path::Path;
use crate::detector::stack::{detect_stack, stack_name};

pub fn execute() -> Result<(), String> {
    let stack = detect_stack();
    let name = stack_name(&stack);
    
    println!("🔍 Detected Stack: {}", name);
    
    // 1. Scaffold .agentrc
    let agentrc_content = format!(
        "# Tether Agent Configuration\n\
        stack: {}\n\
        strict_mode: true\n\
        context_file: .agent-context.md\n\
        rules:\n\
          - Do not hallucinate dependencies.\n\
          - Read .agent-context.md before touching any files.\n\
          - Follow existing architectural patterns.\n",
        name
    );
    
    fs::write(".agentrc", agentrc_content)
        .map_err(|e| format!("Failed to write .agentrc: {}", e))?;
    println!("✅ Created .agentrc");

    // 2. Scaffold .github/SKILLS.md
    fs::create_dir_all(".github").map_err(|e| e.to_string())?;
    let skills_content = "# Agent Skills\n\n\
        This file defines the rigid boundaries for AI execution in this repository.\n\
        1. Context constraint: Always review `.agent-context.md`.\n\
        2. Execution limits: Only modify files related to the specific user prompt.\n";
    
    if !Path::new(".github/SKILLS.md").exists() {
        fs::write(".github/SKILLS.md", skills_content)
            .map_err(|e| format!("Failed to write SKILLS.md: {}", e))?;
        println!("✅ Created .github/SKILLS.md");
    }

    Ok(())
}
EOF

# 9. Write Map Command
cat << 'EOF' > src/commands/map.rs
use ignore::WalkBuilder;
use std::fs;

pub fn execute() -> Result<(), String> {
    println!("🗺️  Mapping context architecture...");

    let mut context_map = String::from("# Repository Architecture Context\n\n");
    context_map.push_str("This map is auto-generated by Tether. Use it to understand the file structure without blowing up context windows.\n\n");
    context_map.push_str("## Directory Tree\n```text\n");

    // Configure the walker to ignore hidden dirs (like .git) but respect .gitignore
    let walker = WalkBuilder::new("./")
        .hidden(true)
        .build();

    for result in walker {
        match result {
            Ok(entry) => {
                let path = entry.path().display().to_string();
                if path != "./" {
                    // Simple indentation based on directory depth
                    let depth = path.split('/').count();
                    let indent = "  ".repeat(depth.saturating_sub(1));
                    let file_name = entry.file_name().to_string_lossy();
                    context_map.push_str(&format!("{}├── {}\n", indent, file_name));
                }
            }
            Err(err) => eprintln!("Warning: Skipping a file due to error: {}", err),
        }
    }

    context_map.push_str("```\n");

    fs::write(".agent-context.md", context_map)
        .map_err(|e| format!("Failed to write context map: {}", e))?;

    println!("✅ Context map written to .agent-context.md");
    Ok(())
}
EOF

# 10. Compile and Verify
echo "Building release binary..."
cargo build --release

echo "Running tests..."
./target/release/tether-cli init
./target/release/tether-cli map

echo "Validating artifacts..."
if [ ! -f ".agentrc" ]; then
  echo "❌ Error: .agentrc was not generated."
  exit 1
fi

if [ ! -f ".github/SKILLS.md" ]; then
  echo "❌ Error: .github/SKILLS.md was not generated."
  exit 1
fi

if [ ! -f ".agent-context.md" ]; then
  echo "❌ Error: .agent-context.md was not generated."
  exit 1
fi

echo "✅ All required files were successfully generated."
echo "✅ Tests passed successfully. Tether is fully operational."
```
