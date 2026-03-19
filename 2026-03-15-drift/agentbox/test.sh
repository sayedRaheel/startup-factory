#!/bin/bash
set -e

echo "[Test] Building AgentBox..."
go build -o agentbox main.go

echo "[Test] Running 'init'..."
./agentbox init

if [ ! -f ".agentbox.yml" ]; then
    echo "❌ Error: .agentbox.yml was not created."
    exit 1
fi

if [ ! -f ".agent-context" ]; then
    echo "❌ Error: .agent-context was not created."
    exit 1
fi

echo "[Test] Testing whitelisted command (ls)..."
./agentbox run ls > /dev/null
echo "✅ Whitelisted command succeeded."

echo "[Test] Testing non-whitelisted command (whoami)..."
if ./agentbox run whoami 2>/dev/null; then
    echo "❌ Error: Non-whitelisted command 'whoami' succeeded. It should have been blocked."
    exit 1
else
    echo "✅ Non-whitelisted command correctly blocked."
fi

echo "🚀 All tests passed successfully!"
exit 0
