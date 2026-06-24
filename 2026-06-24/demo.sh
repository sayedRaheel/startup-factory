#!/usr/bin/env bash
# Quick demo of jsonshape against the bundled fixtures.
set -euo pipefail
cd "$(dirname "$0")"

echo "== tree view =="
python3 jsonshape.py sample.json

echo
echo "== with sample values, depth 2 =="
python3 jsonshape.py --samples --depth 2 sample.json

echo
echo "== NDJSON merge (optional fields flagged) =="
python3 jsonshape.py --ndjson events.ndjson

echo
echo "== piped from stdin =="
echo '[1, "two", null]' | python3 jsonshape.py -
