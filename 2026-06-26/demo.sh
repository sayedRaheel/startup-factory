#!/usr/bin/env bash
# Demo for mdtable: show a messy table being aligned.
set -euo pipefail
cd "$(dirname "$0")"

echo "=== before (sample.md, raw) ==="
cat sample.md

echo
echo "=== after (mdtable sample.md) ==="
python3 mdtable.py sample.md

echo
echo "=== --check on the messy original (expect exit 2) ==="
if python3 mdtable.py --check sample.md; then
  echo "already aligned"
else
  echo "exit code: $?  (needs reformatting)"
fi
