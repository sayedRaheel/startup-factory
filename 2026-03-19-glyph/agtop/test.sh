#!/bin/bash
set -e
echo "Running tests..."
go mod tidy
go test ./...
go build -o bin/agtop main.go
echo "✅ Tests passed"
