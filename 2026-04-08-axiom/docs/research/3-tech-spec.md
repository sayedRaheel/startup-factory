Vera is right. The market is drowning in Kubernetes-deployed, Python-wrapped, over-engineered "context layers" that take 10 minutes to ingest a single repository. We don't need a platform; we need a static binary that executes with the mechanical precision of a sniper rifle.

I am Linus. Let’s architect this.

Here is your Technical Specification and Implementation Plan.

---

### 1. Architectural Decision Record (ADR)

**Decision 1: Language & Compilation Target**
*   **Choice:** Rust.
*   **Rationale:** We need raw CPU performance, memory safety, and—crucially—a single statically linked binary. Hacker News won't install a Python package or a Docker container for a CLI tool.
*   **Trade-off:** Slower iteration speed and complex compilation times compared to Go. However, Rust's ML ecosystem (`candle`) and zero-cost abstractions make it superior for local, on-device silicon execution.

**Decision 2: Vector Storage & Search Algorithm**
*   **Choice:** SQLite (via `rusqlite` with the `bundled` feature) + Brute-Force SIMD In-Memory Search.
*   **Rationale:** Vera’s PRD suggested `libSQL` or `sqlite-vss`. **I am overriding this.** C-based SQLite vector extensions frequently break cross-compilation (stopping our single-binary goal). Here is the architectural reality: A large codebase is ~10,000 files, yielding maybe 50,000 chunks. 50,000 embeddings of 384 dimensions (f32) is ~76MB of data. Loading 76MB into RAM from SQLite and running a brute-force cosine similarity over it in Rust takes less than 10 milliseconds.
*   **Trade-off:** O(N) search time instead of O(log N) HNSW graph traversal. For local codebases, the latency difference is invisible, but we gain 100x simpler builds and a smaller binary. 

**Decision 3: Embedding Execution**
*   **Choice:** HuggingFace `candle` (Rust-native ML framework).
*   **Rationale:** `candle` allows us to run a quantized `all-MiniLM-L6-v2` model purely in Rust, utilizing CPU/Metal/CUDA without requiring external C++ shared libraries like ONNX Runtime (`ort`).
*   **Trade-off:** `candle`'s API is lower-level than Python's `transformers`. We have to manually handle tensor reshaping and tokenization.

---

### 2. The Tech Stack

*   **CLI Routing:** `clap` (feature: `derive`)
*   **Storage:** `rusqlite` (feature: `bundled` - compiles SQLite directly into the binary)
*   **Embeddings:** `candle-core`, `candle-transformers`, `candle-nn`
*   **Tokenization:** `tokenizers`
*   **File Traversal:** `ignore` (respects `.gitignore` exactly like `ripgrep`)
*   **UI/UX:** `indicatif` (progress bars), `colored` (syntax highlighting)

---

### 3. File Structure

```text
vgrep/
├── Cargo.toml
├── src/
│   ├── main.rs      # Entrypoint & CLI execution logic
│   ├── cli.rs       # Clap struct definitions
│   ├── index.rs     # Codebase traversal and chunking logic
│   ├── embed.rs     # Candle ML model wrapper
│   ├── db.rs        # SQLite schema and query logic
│   ├── search.rs    # Vector similarity and formatting (Prompt/CLI)
│   └── utils.rs     # File parsing & text splitting
```

---

### 4. Step-by-Step Execution Commands

Forge, run these exact commands in your terminal to initialize the sniper rifle:

```bash
# 1. Initialize the project
cargo new vgrep
cd vgrep

# 2. Add Core CLI and utility dependencies
cargo add clap --features derive
cargo add colored indicatif
cargo add ignore
cargo add text-splitter

# 3. Add SQLite with bundled C-source
cargo add rusqlite --features bundled

# 4. Add ML & HuggingFace dependencies
cargo add candle-core candle-nn candle-transformers
cargo add tokenizers
cargo add serde --features derive
cargo add serde_json
```

---

### 5. Exact Logic & Boilerplate

Here is the exact code. No bloat. I have written the integration boundaries so you can see exactly how the data flows.

#### `src/cli.rs` (The Interface)
```rust
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "vgrep", about = "Vector grep for your local codebase.", version = "1.0")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Initialize and index the current directory
    Init {
        #[arg(default_value = ".")]
        path: String,
    },
    /// Semantic search the codebase
    Search {
        /// The natural language query
        query: String,
        
        /// Output perfectly formatted XML for LLM prompts
        #[arg(long, short)]
        prompt: bool,
        
        /// Number of results to return
        #[arg(long, short, default_value_t = 5)]
        top_k: usize,
    },
}
```

#### `src/db.rs` (The Storage Layer)
We store the embedding as a raw byte array (`BLOB`) in SQLite to completely bypass complex vector extensions.

```rust
use rusqlite::{params, Connection, Result};

pub fn init_db() -> Result<Connection> {
    // Hidden db folder in the project root
    std::fs::create_dir_all(".vgrep").ok();
    let conn = Connection::open(".vgrep/index.db")?;

    conn.execute(
        "CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY,
            file_path TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding BLOB NOT NULL
        )",
        [],
    )?;

    Ok(conn)
}

pub fn insert_chunk(conn: &Connection, file_path: &str, content: &str, embedding: &[f32]) -> Result<()> {
    // Convert f32 array to raw bytes for SQLite BLOB storage
    let bytes: &[u8] = bytemuck::cast_slice(embedding);
    
    conn.execute(
        "INSERT INTO chunks (file_path, content, embedding) VALUES (?1, ?2, ?3)",
        params![file_path, content, bytes],
    )?;
    Ok(())
}
```

#### `src/embed.rs` (The ML Engine)
*Architect's Note: I'm abstracting the verbose Candle loading logic here. You will implement the `all-MiniLM-L6-v2` tensor manipulation inside `embed_text`.*

```rust
use candle_core::{Device, Tensor};
// use candle_transformers::models::bert::{BertModel, Config};
// use tokenizers::Tokenizer;

pub struct Embedder {
    // model: BertModel,
    // tokenizer: Tokenizer,
    // device: Device,
}

impl Embedder {
    pub fn new() -> Self {
        // TODO: Load quantized MiniLM model and Tokenizer from local cache or HF Hub
        // fallback to CPU if Metal/CUDA is unavailable.
        println!("Loading on-device embedding model...");
        Self {}
    }

    pub fn embed_text(&self, text: &str) -> Vec<f32> {
        // TODO: Tokenize text, pass through BertModel, perform mean pooling.
        // Returning dummy 384-dimensional vector for compilation.
        vec![0.01; 384] 
    }
}
```

#### `src/search.rs` (The Execution Engine)
Brute-force dot product computation. Lightning fast in pure Rust.

```rust
use rusqlite::Connection;
use colored::*;

struct SearchResult {
    file_path: String,
    content: String,
    score: f32,
}

pub fn execute_search(conn: &Connection, query_embedding: &[f32], prompt_mode: bool, top_k: usize) {
    let mut stmt = conn.prepare("SELECT file_path, content, embedding FROM chunks").unwrap();
    let mut rows = stmt.query([]).unwrap();

    let mut results: Vec<SearchResult> = Vec::new();

    while let Some(row) = rows.next().unwrap() {
        let path: String = row.get(0).unwrap();
        let content: String = row.get(1).unwrap();
        let embed_blob: Vec<u8> = row.get(2).unwrap();
        
        // Cast bytes back to f32 slice
        let chunk_embedding: &[f32] = bytemuck::cast_slice(&embed_blob);
        
        // Compute Cosine Similarity (Dot Product if normalized)
        let score: f32 = query_embedding.iter()
            .zip(chunk_embedding.iter())
            .map(|(a, b)| a * b)
            .sum();

        results.push(SearchResult { file_path: path, content, score });
    }

    // Sort descending by score
    results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap());
    let top_results = results.into_iter().take(top_k).collect::<Vec<_>>();

    if prompt_mode {
        print_xml_prompt(top_results);
    } else {
        print_cli(top_results);
    }
}

fn print_cli(results: Vec<SearchResult>) {
    for res in results {
        println!("{}", format!("--> {}", res.file_path).green().bold());
        println!("{}", res.content);
        println!("{}", "---".dimmed());
    }
}

fn print_xml_prompt(results: Vec<SearchResult>) {
    println!("<context>");
    for res in results {
        println!("  <file path=\"{}\">", res.file_path);
        println!("<![CDATA[\n{}\n]]>", res.content);
        println!("  </file>");
    }
    println!("</context>");
}
```

#### `src/main.rs` (The Orchestrator)
```rust
mod cli;
mod db;
mod embed;
mod search;

use clap::Parser;
use cli::{Cli, Commands};
use ignore::WalkBuilder;
use indicatif::ProgressBar;

fn main() {
    let cli = Cli::parse();

    match &cli.command {
        Commands::Init { path } => {
            println!("Initializing vgrep index in {}...", path);
            let conn = db::init_db().expect("Failed to init SQLite");
            let embedder = embed::Embedder::new();
            
            let walker = WalkBuilder::new(path).build();
            let pb = ProgressBar::new_spinner();
            
            for result in walker {
                if let Ok(entry) = result {
                    if entry.file_type().map_or(false, |ft| ft.is_file()) {
                        pb.set_message(format!("Indexing {:?}", entry.path()));
                        // TODO: Read file, chunk text via text-splitter
                        let content = "dummy chunked content"; 
                        let vector = embedder.embed_text(content);
                        
                        db::insert_chunk(&conn, entry.path().to_str().unwrap(), content, &vector)
                            .expect("DB insertion failed");
                    }
                }
            }
            pb.finish_with_message("Done. Codebase indexed natively.");
        }
        Commands::Search { query, prompt, top_k } => {
            let conn = rusqlite::Connection::open(".vgrep/index.db").expect("No index found. Run 'vg init'");
            let embedder = embed::Embedder::new();
            
            let query_vector = embedder.embed_text(query);
            search::execute_search(&conn, &query_vector, *prompt, *top_k);
        }
    }
}
```

### Next Steps for Forge
1. Build the structure exactly as laid out above.
2. Implement the HuggingFace `candle` BERT inference in `embed.rs`. (You will need to fetch the config, tokenizer, and weights for `all-MiniLM-L6-v2` from HF, or bake them into the binary if you want true offline zero-config).
3. Use the `text-splitter` crate inside the `WalkBuilder` loop in `main.rs` to break large files into ~500 token chunks before embedding.

Do not over-engineer this. The value is in the execution speed and the XML prompt piping. Build it.
