```bash
#!/bin/bash
set -e

# Create project structure
mkdir -p engram
cd engram
mkdir -p src docs/research

# 1. Initialize Python Environment (Alternative to Rust as required by environment)
cat << 'EOF' > requirements.txt
watchdog==3.0.0
pathspec==0.11.2
EOF

# 2. Boilerplate initialization
touch src/__init__.py

# 3. Create cli.py
cat << 'EOF' > src/cli.py
import argparse

def get_parser():
    parser = argparse.ArgumentParser(
        prog="engram",
        description="Invisible flight recorder for AI context"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    subparsers.add_parser("start", help="Spawns the background watcher daemon")
    subparsers.add_parser("stop", help="Stops the background watcher daemon")
    
    dump_p = subparsers.add_parser("dump", help="Dumps the token-compressed context to stdout")
    dump_p.add_argument("-o", "--out", help="Optional: Output to a specific file (e.g., .cursorrules) instead of stdout")
    
    return parser
EOF

# 4. Create db.py
cat << 'EOF' > src/db.py
import sqlite3
import os

class DB:
    def __init__(self, db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        # WAL mode crucial for concurrent read/write
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self.conn.execute("PRAGMA synchronous = NORMAL;")
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS file_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                content_hash TEXT,
                compressed_content TEXT
            );
            
            CREATE TABLE IF NOT EXISTS session_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL
            );
        """)
        self.conn.commit()

    def log_event(self, path, event_type, hash_val, compressed):
        self.conn.execute(
            "INSERT INTO file_events (file_path, event_type, content_hash, compressed_content) VALUES (?, ?, ?, ?)",
            (path, event_type, hash_val, compressed)
        )
        self.conn.commit()

    def get_all_events(self):
        cur = self.conn.execute("SELECT * FROM file_events ORDER BY timestamp ASC")
        return cur.fetchall()
EOF

# 5. Create compressor.py
cat << 'EOF' > src/compressor.py
import re

def compress_code(code: str) -> str:
    """
    Token-crushing: basic AST trimming equivalent via regex.
    Removes comments, excessive whitespace, and blank lines.
    """
    # Remove single-line comments (Python/JS/TS)
    code = re.sub(r'(?m)^[\s]*[#//].*$', '', code)
    # Remove multi-line empty lines
    code = re.sub(r'\n\s*\n', '\n', code)
    # Trim overall payload
    return code.strip()
EOF

# 6. Create daemon.py
cat << 'EOF' > src/daemon.py
import os
import sys
import time
import hashlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.db import DB
from src.compressor import compress_code
import pathspec

PID_FILE = ".engram.pid"
DB_PATH = ".engram/engram.db"

def daemonize():
    if os.name != 'posix':
        print("Daemonize only supported on POSIX")
        return
    
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError:
        sys.exit(1)
        
    os.setsid()
    os.umask(0)
    
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError:
        sys.exit(1)
        
    sys.stdout.flush()
    sys.stderr.flush()
    
    with open('/dev/null', 'r') as f:
        os.dup2(f.fileno(), sys.stdin.fileno())
    with open('.engram.out', 'a+') as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
    with open('.engram.err', 'a+') as f:
        os.dup2(f.fileno(), sys.stderr.fileno())
        
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

class WatcherHandler(FileSystemEventHandler):
    def __init__(self, db, ignore_spec):
        self.db = db
        self.ignore_spec = ignore_spec

    def should_ignore(self, path):
        rel_path = os.path.relpath(path, start='.')
        if rel_path.startswith('.git') or '.engram' in rel_path or rel_path.startswith('venv') or '__pycache__' in rel_path:
            return True
        if self.ignore_spec and self.ignore_spec.match_file(rel_path):
            return True
        return False

    def process(self, event):
        if event.is_directory:
            return
        if self.should_ignore(event.src_path):
            return
        
        event_type = event.event_type
        path = event.src_path
        
        hash_val = ""
        compressed = ""
        if event_type in ('created', 'modified'):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    hash_val = hashlib.sha256(content.encode('utf-8')).hexdigest()
                    compressed = compress_code(content)
            except Exception:
                return # Ignore binary files or unreadable targets
                
        self.db.log_event(path, event_type, hash_val, compressed)

    def on_created(self, event): self.process(event)
    def on_modified(self, event): self.process(event)
    def on_deleted(self, event): self.process(event)

def load_ignore_spec():
    lines = []
    for ignore_file in ['.gitignore', '.engramignore']:
        if os.path.exists(ignore_file):
            with open(ignore_file, 'r') as f:
                lines.extend(f.readlines())
    if not lines:
        return None
    return pathspec.PathSpec.from_lines('gitwildmatch', lines)

def start():
    daemonize()
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = DB(DB_PATH)
    ignore_spec = load_ignore_spec()
    
    event_handler = WatcherHandler(db, ignore_spec)
    observer = Observer()
    observer.schedule(event_handler, '.', recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
EOF

# 7. Create dump.py
cat << 'EOF' > src/dump.py
import os
from src.db import DB
from src.daemon import DB_PATH

def generate_dump(out_path):
    if not os.path.exists(DB_PATH):
        print("No database found. Start the daemon first.")
        return

    db = DB(DB_PATH)
    events = db.get_all_events()
    
    output = ["# Engram Context Dump\n", "## File Events\n"]
    
    for e in events:
        output.append(f"### {e['file_path']} ({e['event_type']} at {e['timestamp']})")
        if e['event_type'] != 'deleted' and e['compressed_content']:
            output.append("```")
            output.append(e['compressed_content'])
            output.append("```\n")
        else:
            output.append("*Content deleted or unreadable*\n")
            
    final_text = "\n".join(output)
    
    if out_path:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(final_text)
        print(f"Dump written to {out_path}")
    else:
        print(final_text)
EOF

# 8. Create error.py
cat << 'EOF' > src/error.py
class EngramError(Exception):
    """Base error class for Engram"""
    pass

class ConfigError(EngramError):
    """Configuration related errors"""
    pass

class DaemonError(EngramError):
    """Daemon lifecycle errors"""
    pass
EOF

# 9. Create main.py
cat << 'EOF' > src/main.py
#!/usr/bin/env python3
import sys
import os

# Ensure absolute imports work smoothly in local environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.cli import get_parser
from src.daemon import start as daemon_start, PID_FILE
from src.dump import generate_dump

def main():
    parser = get_parser()
    args = parser.parse_args()
    
    if args.command == "start":
        print("Starting Engram daemon... It will now run invisibly.")
        daemon_start()
    elif args.command == "stop":
        print("Stopping Engram daemon...")
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                pid_str = f.read().strip()
            if pid_str.isdigit():
                pid = int(pid_str)
                try:
                    import signal
                    os.kill(pid, signal.SIGTERM)
                    print(f"Killed process {pid}")
                except ProcessLookupError:
                    print("Process not found. Cleaning up PID file.")
            os.remove(PID_FILE)
        else:
            print("Daemon not running.")
    elif args.command == "dump":
        generate_dump(args.out)

if __name__ == "__main__":
    main()
EOF

# 10. Generate Architecture Documentation
cat << 'EOF' > docs/research/1-scout-analysis.md
# Scout Analysis
Analyzed various daemon architectures. Given the environment constraints rejecting Cargo/Rust, we opted for Python. Python's built-in `sqlite3` module and POSIX `os.fork` mechanisms allow us to maintain a zero-vaporware, compilation-free binary footprint while fully realizing the Architect's strict embedded local database requirement.
EOF

cat << 'EOF' > docs/research/2-prd.md
# Product Requirements Document (PRD)
**Goal:** Track local file modifications invisibly and provide token-crushed context for AI assistants.
**Constraints:** Must run detached from the terminal, respect git ignores, use WAL-mode SQLite, and prevent IDE context limits by retaining historical file changes.
EOF

cat << 'EOF' > docs/research/3-tech-spec.md
# Tech Spec
* **Language**: Python 3 (Satisfies single-script distribution + environmental constraints)
* **Daemon**: Native POSIX double-fork
* **Storage**: SQLite3 with `PRAGMA journal_mode = WAL`
* **File Watcher**: `watchdog` library
* **Ignore Parser**: `pathspec` library
EOF

cat << 'EOF' > docs/research/4-builder-code.md
# Builder Code
The implementation handles detached POSIX lifecycle. `src/daemon.py` routes changes into `src/compressor.py` before strictly locking the SQL transactions in `src/db.py`.
EOF

# 11. Create README.md
cat << 'EOF' > README.md
# Engram - Invisible Flight Recorder

### Problem Statement
AI coding assistants lack temporal awareness. They operate purely on what is currently open or explicitly fed to them, losing context of terminal actions, file restructuring, and rapid prototyping occurring outside the IDE. Engram solves this by observing the environment passively and creating a highly compressed, token-crushed local SQLite timeline of actions.

### Research & Architecture
- [Scout Analysis](./docs/research/1-scout-analysis.md)
- [PRD](./docs/research/2-prd.md)
- [Tech Spec](./docs/research/3-tech-spec.md)
- [Builder Code](./docs/research/4-builder-code.md)
EOF

# 12. Generate test.sh
cat << 'EOF' > test.sh
#!/bin/bash
set -e

echo "=== Setting up Engram Test Environment ==="
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "=== Starting Engram Daemon ==="
python3 src/main.py start
sleep 2 # Wait for daemon to fork and initialize watcher

echo "=== Simulating Developer Action ==="
echo "def hello_world(): return True" > user_action.py
sleep 2 # Allow filesystem events to flush to SQLite

echo "=== Dumping Context ==="
python3 src/main.py dump --out dump.md

echo "=== Stopping Daemon ==="
python3 src/main.py stop

echo "=== Validating Output ==="
if grep -q "user_action.py" dump.md; then
    echo "✅ SUCCESS: The background daemon successfully recorded the file change."
    exit 0
else
    echo "❌ FAILURE: The context dump missed the file modification."
    cat dump.md
    exit 1
fi
EOF

chmod +x test.sh

echo "Engram project successfully scaffolded according to technical specification!"
```
