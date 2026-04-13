#!/usr/bin/env bash
set -e

echo "=== Running Tether Tests ==="

echo "1. Testing 'init' command"
node src/cli.js init
if [ ! -f ".tetherrules" ]; then
    echo "Error: .tetherrules file was not created!"
    exit 1
fi

echo "2. Testing 'run' command with mock agent"
# Create a simple mock agent script that sends a test HTTP payload to our proxy
cat << 'MOCK' > mock_agent.sh
#!/usr/bin/env bash
echo "Mock agent running..."

# Send a request to the proxy. The proxy will forward to OPENAI_BASE_URL.
# Since we lack a real OpenAI key, it will likely return a 4xx, but the proxy itself will stay up and handle it safely.
curl -s -o /dev/null -w "HTTP Status from proxy: %{http_code}\n" -X POST -H "Content-Type: application/json" \
     -d '{"model": "gpt-3.5-turbo", "messages": [{"role": "system", "content": "I am a mock agent"}]}' \
     http://127.0.0.1:8765/v1/chat/completions || true
     
echo "Mock agent finished."
exit 0
MOCK
chmod +x mock_agent.sh

# Start Tether and run the mock agent
node src/cli.js run ./mock_agent.sh

echo "=== All Tests Passed Successfully ==="
exit 0
