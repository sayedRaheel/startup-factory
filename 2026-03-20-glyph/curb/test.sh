#!/bin/bash
set -e

echo "Building Curb..."
go build -o curb_bin ./cmd/curb

echo "Running tests..."
go test ./...

echo "✅ Test passed! Compilation successful."
