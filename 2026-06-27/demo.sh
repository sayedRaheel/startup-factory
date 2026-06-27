#!/usr/bin/env bash
# Demo for curl2code. Run: bash demo.sh
set -euo pipefail
cd "$(dirname "$0")"

run() {
  echo "+ $1"
  echo "----------------------------------------"
  eval "$1"
  echo
}

echo "### 1) Browser 'Copy as cURL' -> Python (requests)"
run "python3 curl2code.py -t python \"curl 'https://api.example.com/v1/users' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer tok_123' \
  --data-raw '{\\\"name\\\":\\\"Ada\\\",\\\"active\\\":true}'\""

echo "### 2) Same command -> JavaScript fetch"
run "python3 curl2code.py -t fetch \"curl 'https://api.example.com/v1/users' \
  -X POST -H 'Content-Type: application/json' \
  --data-raw '{\\\"name\\\":\\\"Ada\\\"}'\""

echo "### 3) GET with query params (-G) and basic auth -> HTTPie"
run "python3 curl2code.py -t httpie \
  'curl -G -d q=cli -u me:secret https://api.example.com/search'"

echo "### 4) Piped from stdin (e.g. from your clipboard)"
run "echo \"curl -H 'Accept: application/json' https://example.com\" \
  | python3 curl2code.py"

echo "Done."
