This is Linus.

Vera’s PRD is refreshingly ruthless. The market is drowning in heavyweight, over-engineered agent frameworks that try to be the brain, the hands, and the compiler. We don’t need to build another brain. We just need to build the absolute best pair of blinders for existing brains.

Every system outlives the team that built it, provided it’s built on solid architectural foundations. We are going to build a completely stateless, extremely fast CLI tool.

Here is the technical specification and execution plan for Forge.

***

### 1. Architectural Decision Record (ADR)

**Language: Rust**
*   **Why:** We are optimizing for distribution and developer experience. A CLI tool that requires installing Node.js or Python is dead on arrival for infrastructure or backend engineers. Rust compiles to a statically linked, zero-dependency binary. It executes in milliseconds. We will use the `ignore` crate (the same engine powering `ripgrep`) to traverse directories exponentially faster than standard library walkers, effortlessly respecting `.gitignore`.
*   **Trade-off:** Rust has slower compile times and a steeper learning curve for future open-source contributors compared to Go. However, the ecosystem around CLI parsing (`clap`) and fast file-system traversal (`ignore`) makes it the superior choice for this specific domain.

**Database: None (Stateless)**
*   **Why:** Tether is a scaffolding and transformation pipeline. State does not belong in our application; it belongs in the filesystem we are augmenting.
*   **Trade-off:** We cannot track historical runs or analytics. This is a feature, not a bug. It guarantees privacy and zero lock-in.

***

### 2. Tech Stack & Libraries

*   **Compiler:** Rust (Edition 2021)
*   **CLI Parser:** `clap` (v4 with `derive` features) — Standardizes our input parsing instantly.
*   **Filesystem Traversal:** `ignore` (v0.4) — Fast directory traversal that respects `.gitignore` out of the box.
*   **Serialization:** `serde` / `serde_json` — For reading stack manifests (like `package.json`) if necessary, and potentially writing structured outputs.

***

### 3. File Structure

```text
tether/
├── Cargo.toml
└── src/
    ├── main.rs            # Entrypoint
    ├── cli.rs             # CLI arguments and routing structure
    ├── commands/
    │   ├── mod.rs         # Command exports
    │   ├── init.rs        # Stack profiling & `.agentrc` scaffold
    │   └── map.rs         # Context graph generation
    └── detector/
        ├── mod.rs         # Detector exports
        └── stack.rs       # Language & framework heuristics
```

***

### 4. Step-by-Step Execution Commands

Forge, run exactly these commands to scaffold the workspace:

```bash
cargo new tether
cd tether
cargo add clap --features derive
cargo add ignore
cargo add serde --features derive
cargo add serde_json

mkdir -p src/commands src/detector
touch src/cli.rs src/commands/mod.rs src/commands/init.rs src/commands/map.rs src/detector/mod.rs src/detector/stack.rs
```

***

### 5. Exact Logic & Boilerplate Code

Forge, implement the following files exactly. They contain the architectural skeleton, error boundaries, and core logic.

#### `Cargo.toml`
Ensure your dependencies look like this:
```toml
[package]
name = "tether-cli"
version = "0.1.0"
edition = "2021"

[dependencies]
clap = { version = "4.4", features = ["derive"] }
ignore = "0.4"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
```

#### `src/main.rs`
The entrypoint must be clean and purely responsible for routing the command.

```rust
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
```

#### `src/cli.rs`
Define the strict CLI interface using `clap`.

```rust
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
```

#### `src/detector/mod.rs`
```rust
pub mod stack;
```

#### `src/detector/stack.rs`
The heuristic engine. We look for definitive markers of a stack.

```rust
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
```

#### `src/commands/mod.rs`
```rust
pub mod init;
pub mod map;
```

#### `src/commands/init.rs`
This command generates the static rules of engagement.

```rust
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
```

#### `src/commands/map.rs`
This generates the crucial context graph using `ignore`.

```rust
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
```

***

### Handoff to Forge

Forge, you have your boundaries, your stack, and your raw components. Do not add random dependencies. Do not implement a background daemon. Take this spec, stitch it together, run `cargo build --release`, and ship a tight, lethal binary.
