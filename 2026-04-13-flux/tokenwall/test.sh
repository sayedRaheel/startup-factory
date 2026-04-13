#!/bin/bash
set -e

echo "=> Starting TokenWall Proxy Background Process..."
export BUDGET=5.0
export PORT=8080
node src/index.js &
SERVER_PID=$!

# Wait for server initialization
sleep 2

echo "=> Executing Test Request against /v1/chat/completions..."

# We fire a request through our proxy to OpenAI.
# We do not provide a real API key. 
# Success condition: The proxy correctly routes the request, the HTTP request finishes, 
# and OpenAI returns a 401 Unauthorized (which the proxy successfully pipes back).
RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/tokenwall_response.txt -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Analyze <file name="local.rs">fn main() {}</file>"}
    ]
  }')

HTTP_STATUS=$(echo "$RESPONSE" | tail -n1)

echo "=> Proxy responded with HTTP Status: $HTTP_STATUS"
cat /tmp/tokenwall_response.txt
echo ""

kill $SERVER_PID

if [ "$HTTP_STATUS" -eq 401 ]; then
    echo "========================================================="
    echo "[SUCCESS] Proxy intercepted, parsed, and forwarded flawlessly."
    echo "[SUCCESS] Received expected 401 from OpenAI."
    echo "========================================================="
    exit 0
else
    echo "========================================================="
    echo "[FAILURE] Expected 401, but got $HTTP_STATUS. Proxy failed."
    echo "========================================================="
    exit 1
fi
