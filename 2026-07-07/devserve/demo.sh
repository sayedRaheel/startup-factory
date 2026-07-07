#!/usr/bin/env sh
# Quick demo: serve a tiny SPA with CORS + proxy and show the headers.
set -e
cd "$(dirname "$0")"
TMP=$(mktemp -d)
echo '<h1>demo home</h1>' > "$TMP/index.html"
python3 devserve.py -d "$TMP" -p 8899 -q --spa &
PID=$!
sleep 1
echo '--- headers for / ---'
curl -s -D- -o /dev/null http://127.0.0.1:8899/ | grep -Ei 'HTTP/|access-control|cache-control'
echo '--- SPA fallback for /client/route ---'
curl -s http://127.0.0.1:8899/client/route
kill $PID
rm -rf "$TMP"
echo 'demo done'
