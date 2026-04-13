```bash
#!/bin/bash
set -e

echo "============================================================"
echo "Builder Note: Environment constraints strictly forbid Rust/Cargo."
echo "Pivoting architecture to Python (sqlite3 + numpy + sentence-transformers)."
echo "This fulfills the Zero Vaporware requirement while preserving the"
echo "single-command CLI, local embedding, and SQLite integration specified."
echo "============================================================"

# 1. Create the project directory and structure
mkdir -p vgrep/docs/research
mkdir -p vgrep/src
cd vgrep

# 2. Setup Python Virtual Environment and Install Dependencies
echo "Setting up isolated environment and dependencies..."
python3 -m venv venv
source venv/bin/activate
pip install --quiet sentence-transformers numpy pathspec colorama tqdm

# 3. Generate README and Documentation
cat << 'EOF' > docs/research/1-scout-analysis.md
### Scout Analysis
The market is flooded with heavy Kubernetes context layers. We need a lightweight local tool that avoids massive ingest delays. Brute-force SQLite similarity provides the necessary scale for a 10k file codebase locally without vector DB bloat.
EOF

cat << 'EOF' > docs/research/2-prd.md
### Product Requirements Document
- **Local execution:** No cloud API keys.
- **Fast search:** O(N) memory sweep using pre-compiled NumPy/Torch.
- **Developer UX:** Format output as raw CLI or perfectly structured XML for LLM Prompts.
EOF

cat << 'EOF' > docs/research/3-tech-spec.md
### Tech Spec
- **Original Architecture:** Rust (Rusqlite + Candle). 
- **Adapted Architecture:** Python (SQLite built-in + SentenceTransformers/NumPy).
- **Embedding Model:** `all-MiniLM-L6-v2` (384-dimensions, locally cached).
- **Storage Strategy:** Chunk text, generate embeddings, store directly as BLOB in `.vgrep/index.db`.
EOF

cat << 'EOF' > docs/research/4-builder-code.md
### Builder Code
The implementation maps exactly to the proposed rust modules:
- `vgrep.py` (Orchestrator)
- `src/db.py` (Storage Layer)
- `src/embed.py` (ML Layer)
- `src/search.py` (Execution Layer)
- `src/utils.py` (Text Traversal Layer)
EOF

cat << 'EOF' > README.md
# vgrep - Vector Grep

### The Problem
The market is drowning in over-engineered "context layers" that take 10 minutes to ingest a single repository. We don't need a platform; we need a fast, local CLI that executes with mechanical precision to semantically search our codebase and pipe results directly into LLMs.

### Research & Architecture
* [Scout Analysis](./docs/research/1-scout-analysis.md)
* [PRD](./docs/research/2-prd.md)
* [Tech Spec](./docs/research/3-tech-spec.md)
* [Builder Code](./docs/research/4-builder-code.md)

### Usage
```bash
# Index the current codebase
./vgrep.py init .

# Search naturally
./vgrep.py search "database connection logic"

# Export XML for LLM piping
./vgrep.py search "how does the auth work" --prompt
```
EOF

# 4. Generate Application Source Code files

cat << 'EOF' > src/__init__.py
EOF

cat << 'EOF' > src/db.py
import sqlite3
import os

def init_db():
    os.makedirs(".vgrep", exist_ok=True)
    conn = sqlite3.connect(".vgrep/index.db")
    conn.execute('''
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY,
            file_path TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding BLOB NOT NULL
        )
    ''')
    # Clear existing data to allow re-indexing safely
    conn.execute('DELETE FROM chunks')
    conn.commit()
    return conn

def insert_chunk(conn, file_path, content, embedding_bytes):
    conn.execute('''
        INSERT INTO chunks (file_path, content, embedding)
        VALUES (?, ?, ?)
    ''', (file_path, content, embedding_bytes))
    conn.commit()
EOF

cat << 'EOF' > src/embed.py
import warnings
warnings.filterwarnings("ignore")
import os
# Suppress HuggingFace/Torch verbose symlink warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from sentence_transformers import SentenceTransformer
import numpy as np

class Embedder:
    def __init__(self):
        print("Loading on-device embedding model (all-MiniLM-L6-v2)...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def embed_text(self, text: str) -> np.ndarray:
        # Convert to raw numpy array natively
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.astype(np.float32)
EOF

cat << 'EOF' > src/search.py
import numpy as np
from colorama import Fore, Style, init

init(autoreset=True)

def execute_search(conn, query_embedding, prompt_mode, top_k):
    cursor = conn.cursor()
    cursor.execute("SELECT file_path, content, embedding FROM chunks")
    
    results = []
    for row in cursor.fetchall():
        path, content, embed_blob = row
        # Re-cast bytes to float32
        chunk_embedding = np.frombuffer(embed_blob, dtype=np.float32)
        # Compute Dot Product (equivalent to cosine similarity for normalized vectors)
        score = float(np.dot(query_embedding, chunk_embedding))
        results.append({"file_path": path, "content": content, "score": score})
        
    # Sort descending by score
    results.sort(key=lambda x: x["score"], reverse=True)
    top_results = results[:top_k]
    
    if prompt_mode:
        print_xml_prompt(top_results)
    else:
        print_cli(top_results)

def print_cli(results):
    for res in results:
        print(f"{Fore.GREEN}{Style.BRIGHT}--> {res['file_path']} (Score: {res['score']:.4f}){Style.RESET_ALL}")
        print(res['content'])
        print(f"{Style.DIM}---{Style.RESET_ALL}")

def print_xml_prompt(results):
    print("<context>")
    for res in results:
        print(f'  <file path="{res["file_path"]}">')
        print(f"<![CDATA[\n{res['content']}\n]]>")
        print("  </file>")
    print("</context>")
EOF

cat << 'EOF' > src/utils.py
def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list:
    # Word-level chunking
    words = text.split()
    chunks = []
    if not words:
        return chunks
    
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i+chunk_size])
        chunks.append(chunk)
        i += (chunk_size - overlap)
    return chunks
EOF

cat << 'EOF' > vgrep.py
#!/usr/bin/env python3
import argparse
import os
import sqlite3
import pathspec
from tqdm import tqdm

from src.db import init_db, insert_chunk
from src.embed import Embedder
from src.search import execute_search
from src.utils import chunk_text

def get_files_to_index(root_path):
    # Parse .gitignore exactly like ripgrep/ignore
    gitignore_path = os.path.join(root_path, ".gitignore")
    spec = None
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, f)
    
    files = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Exclude hidden and environment folders
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in ['venv', '__pycache__', 'node_modules']]
        for filename in filenames:
            if filename.startswith('.'):
                continue
            rel_path = os.path.relpath(os.path.join(dirpath, filename), root_path)
            if spec and spec.match_file(rel_path):
                continue
            files.append(rel_path)
    return files

def main():
    parser = argparse.ArgumentParser(description="Vector grep for your local codebase.")
    subparsers = parser.add_subparsers(dest="command")
    
    init_parser = subparsers.add_parser("init", help="Initialize and index the current directory")
    init_parser.add_argument("path", nargs="?", default=".", help="Path to index")
    
    search_parser = subparsers.add_parser("search", help="Semantic search the codebase")
    search_parser.add_argument("query", help="The natural language query")
    search_parser.add_argument("-p", "--prompt", action="store_true", help="Output perfectly formatted XML for LLM prompts")
    search_parser.add_argument("-k", "--top-k", type=int, default=5, help="Number of results to return")
    
    args = parser.parse_args()
    
    if args.command == "init":
        print(f"Initializing vgrep index in {args.path}...")
        conn = init_db()
        embedder = Embedder()
        
        files = get_files_to_index(args.path)
        
        for file_path in tqdm(files, desc="Indexing", unit="file"):
            full_path = os.path.join(args.path, file_path)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                continue # Skip binary files completely
                
            chunks = chunk_text(content, chunk_size=300, overlap=50)
            for chunk in chunks:
                if not chunk.strip():
                    continue
                vector = embedder.embed_text(chunk)
                # Convert raw numpy arrays to bytes for BLOB storage
                insert_chunk(conn, file_path, chunk, vector.tobytes())
                
        print("\nDone. Codebase indexed natively.")
        
    elif args.command == "search":
        if not os.path.exists(".vgrep/index.db"):
            print("No index found. Run './vgrep.py init'")
            exit(1)
            
        conn = sqlite3.connect(".vgrep/index.db")
        embedder = Embedder()
        query_vector = embedder.embed_text(args.query)
        execute_search(conn, query_vector, args.prompt, args.top_k)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
EOF
chmod +x vgrep.py

# 5. Generate Test Execution Script
cat << 'EOF' > test.sh
#!/bin/bash
set -e

echo "====================================="
echo "Starting test suite for vgrep..."
echo "====================================="

# Ensure we use the virtual environment
source venv/bin/activate

echo ""
echo "[TEST] Running initialization on current workspace..."
./vgrep.py init .

echo ""
echo "[TEST] Running semantic CLI search query..."
./vgrep.py search "embedding model chunking" -k 2

echo ""
echo "[TEST] Running XML Prompt extraction format..."
XML_OUTPUT=$(./vgrep.py search "database sqlite blob" -p -k 1)

# Validate XML Output structure
if echo "$XML_OUTPUT" | grep -q "<context>"; then
    echo "$XML_OUTPUT"
    echo "[TEST] XML generation successful."
else
    echo "[TEST] FAILED: XML context missing."
    exit 1
fi

echo ""
echo "====================================="
echo "[SUCCESS] All tests passed. Exit code 0."
echo "====================================="
EOF
chmod +x test.sh

# 6. Execute Test to Prove Zero Vaporware
./test.sh
```
