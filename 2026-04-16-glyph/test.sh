#!/bin/bash
set -e

cd ctx_project

echo "Building ctx binary..."
cargo build --release
cp target/release/ctx ctx_bin

echo "Testing feed command (no events yet)..."
./ctx_bin feed

echo "Starting daemon..."
./ctx_bin start

# Wait a moment for watcher to spin up
sleep 2

echo "Modifying file to trigger event..."
touch test_event_file.txt
echo "hello context watcher" > test_event_file.txt

# Wait a moment for event to be processed and written to SQLite
sleep 2

echo "Testing feed command (with events)..."
OUTPUT=$(./ctx_bin feed)
echo "$OUTPUT"

echo "Validating event in feed output..."
if echo "$OUTPUT" | grep -q "file_change.*test_event_file.txt"; then
    echo "Success: Event successfully recorded and retrieved!"
else
    echo "Error: Failed to find event in feed"
    ./ctx_bin stop || true
    exit 1
fi

echo "Stopping daemon..."
./ctx_bin stop || true

echo "All tests passed successfully!"
rm -f test_event_file.txt
