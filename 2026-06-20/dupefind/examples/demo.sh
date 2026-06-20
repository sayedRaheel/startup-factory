#!/usr/bin/env sh
# Reproduce a tiny duplicate-file scenario and run dupefind on it.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
echo "Scanning $HERE ..."
python3 "$HERE/../dupefind.py" "$HERE"
