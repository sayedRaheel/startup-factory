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
