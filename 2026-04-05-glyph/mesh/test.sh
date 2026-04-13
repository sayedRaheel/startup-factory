#!/bin/bash
set -e

echo "Building Mesh binary..."
go build -o mesh

# Clean up to guarantee a pristine test state
rm -f mesh.yml

echo "Testing 'mesh init'..."
./mesh init
if [ ! -f "mesh.yml" ]; then
    echo "❌ Error: mesh.yml was not created."
    exit 1
fi

echo "Testing 'mesh run'..."
OUTPUT=$(./mesh run "Create a python script" --config mesh.yml)
echo "$OUTPUT"

# Verification
if echo "$OUTPUT" | grep -q "Translating prompt to architecture..."; then
    echo "✅ Test Passed: System piped payload effectively via default swarm."
    exit 0
else
    echo "❌ Test Failed: Expected payload output not found."
    exit 1
fi
