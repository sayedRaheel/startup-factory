#!/bin/bash
set -e
echo "Running ctx-surgeon smoke test..."
./bin/ctx-surgeon . > /dev/null
echo "✅ Passed"
