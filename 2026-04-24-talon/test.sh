#!/usr/bin/env bash
set -e

echo "Starting rigorous testing..."

# Navigate to the project directory
cd squelch

# 1. Build the Rust binary
cargo build --release

# 2. Setup environment with mocked secrets to test redaction
echo "SUPER_SECRET_KEY=1234567890abcdef" > .env
echo "SHORT=123" >> .env

# 3. Create test input imitating MCP JSON-RPC messages
cat << 'JSON' > test_input.jsonl
{"jsonrpc": "2.0", "id": 1, "method": "initialize"}
{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "squelched_shell", "arguments": {"command": "echo 'Testing secret: 1234567890abcdef and short: 123'"}}}
JSON

echo "Running Squelch tests..."

# 4. Attempt to run the execution code
./target/release/squelch < test_input.jsonl > test_output.jsonl || {
    echo "ERROR: Failed to run Squelch MCP Server."
    exit 1
}

echo "--- Test Output ---"
cat test_output.jsonl
echo "-------------------"

# 5. Ensure that there was no Vaporware output
if grep -q "1234567890abcdef" test_output.jsonl; then
    echo "TEST FAILED: Secret was exposed in the output!"
    exit 1
fi

if grep -q "\[REDACTED_SECRET\]" test_output.jsonl; then
    echo "TEST PASSED: Long secret successfully redacted."
else
    echo "TEST FAILED: Redaction placeholder not found!"
    exit 1
fi

if grep -q "short: 123" test_output.jsonl; then
    echo "TEST PASSED: Short text (< 6 chars) was preserved as expected."
else
    echo "TEST FAILED: Short text was improperly redacted."
    exit 1
fi

echo "All tests completed successfully. Zero vaporware confirmed."
exit 0
