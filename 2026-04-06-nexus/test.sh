#!/bin/bash
set -e
echo "--- Running Siphon Build & Test ---"
cd siphon
go build -ldflags="-s -w" -o siphon
echo "Binary built successfully. Running tests..."
./siphon . > output.txt
if grep -q "<file path=\"main.go\">" output.txt && grep -q "</file>" output.txt; then
    echo "[PASS] Siphon successfully processed its own files and outputted correct structure."
else
    echo "[FAIL] Output structure is incorrect."
    exit 1
fi
./siphon . -max-tokens 10 > truncate_output.txt
if grep -q "<!-- MAX TOKENS REACHED. TRUNCATED. -->" truncate_output.txt; then
    echo "[PASS] Token truncating functioned correctly."
else
    echo "[FAIL] Token limiting failed to truncate."
    exit 1
fi
echo "All tests passed cleanly. System is ready."
exit 0
