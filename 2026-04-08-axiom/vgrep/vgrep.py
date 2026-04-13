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
