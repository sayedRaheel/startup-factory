#!/usr/bin/env bash
# Demo for jsondiff. Run: bash demo.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "### 1. before.json is pretty-printed; after.json is minified with keys"
echo "###    in a different order. A plain text diff would be a mess - jsondiff"
echo "###    shows only the real changes:"
echo
python3 jsondiff.py before.json after.json --no-color || true

echo
echo "### 2. Arrays compared by position by default; tags were just reordered."
echo "###    With --ignore-array-order the tag reorder disappears:"
echo
python3 jsondiff.py before.json after.json --no-color --ignore-array-order || true

echo
echo "### 3. Machine-readable output for scripts/CI (--format json):"
echo
python3 jsondiff.py before.json after.json --format json || true

echo
echo "### 4. Exit code is 1 when files differ, 0 when identical (great for CI):"
python3 jsondiff.py before.json after.json --quiet && echo "same" || echo "exit code: $?"
