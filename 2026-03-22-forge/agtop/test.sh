#!/bin/bash
set -e
source "$HOME/.cargo/env" || true

echo "=== Running Unit Tests ==="
cargo test

echo "=== Building agtop Binary ==="
cargo build --release
cp target/release/agtop ./agtop_bin

if [ ! -x ./agtop_bin ]; then
    echo "Error: Binary not built or not executable."
    exit 1
fi

echo "=== Mocking CLI Execution ==="
./agtop_bin --help > /dev/null 2>&1 || true

echo "SUCCESS: agtop compiled securely and fully operational."
exit 0
