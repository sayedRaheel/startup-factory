#!/bin/bash
set -e

echo "=========================================="
echo " Running Vigil Integration Test Suite"
echo "=========================================="

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "1. Installing Node.js CLI dependencies..."
cd vigil-cli
npm install > /dev/null 2>&1
cd ..

echo "2. Starting CLI websocket server in background..."
# We run a lightweight headless version of the server to test IPC without blocking the CI with a TUI
cat << 'MOCKEOF' > vigil-cli/test-server.js
const WebSocket = require('ws');
const wss = new WebSocket.Server({ port: 8084 });
console.log("[Node.js] Headless WS server listening on 8084.");
wss.on('connection', ws => {
  ws.on('message', msg => {
    console.log("[Node.js] Received telemetry:", msg.toString());
  });
});
// Auto-kill after 5s to prevent hanging
setTimeout(() => process.exit(0), 5000);
MOCKEOF

cd vigil-cli
node test-server.js &
SERVER_PID=$!
cd ..

# Give the server a moment to bind the port
sleep 1

echo "3. Setting up Python SDK environment..."
cd vigil-python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt > /dev/null 2>&1

echo "4. Running Python Example against the CLI server..."
python example.py

# Cleanup
kill $SERVER_PID 2>/dev/null || true

echo "=========================================="
echo " All tests completed successfully! (Exit 0)"
echo "=========================================="
exit 0
