#!/usr/bin/env bash
# Demo of todotrack against the bundled sample_project/.
set -e
cd "$(dirname "$0")"

echo "== text (default) =="
python3 todotrack.py sample_project --no-color

echo
echo "== markdown =="
python3 todotrack.py sample_project --format markdown

echo
echo "== json, only FIXME/BUG =="
python3 todotrack.py sample_project --format json --tags FIXME,BUG

echo
echo "== CI gate: fail if any FIXME present =="
if python3 todotrack.py sample_project --fail-on FIXME --no-summary >/dev/null; then
  echo "exit 0 (clean)"
else
  echo "exit $? (FIXME found -> CI would fail)"
fi
