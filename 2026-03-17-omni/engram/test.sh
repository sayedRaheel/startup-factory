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
