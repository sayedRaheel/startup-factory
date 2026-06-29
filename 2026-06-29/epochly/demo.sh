#!/usr/bin/env bash
# Quick tour of epochly. Run: bash demo.sh
set -e
cd "$(dirname "$0")"

run() { echo "\$ epochly $*"; python3 epochly.py "$@"; echo; }

echo "# epochly demo"
echo
run 1704067200
run 1704067200000
run '2024-01-01T00:00:00Z'
run now
run diff 1704067200 1704153600
run 1704067200 --unit ms --format '%Y/%m/%d %H:%M'
run 1704067200 --json
