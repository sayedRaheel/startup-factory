#!/bin/bash
set -e
echo "Running tests for agtop..."
go mod tidy
go test -v ./...
go build -o bin/agtop main.go
echo "✅ Tests passed. Binary built at bin/agtop."
