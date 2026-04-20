#!/bin/bash
set -e

echo "--- Building AgentMux Binary ---"
go build -o agentmux

echo "--- Running init ---"
./agentmux init

echo "--- Setting up test configuration ---"
cat << 'YAMLEOF' > agents.yaml
port: 8080
routes:
  - path: "/v1/test"
    primary:
      url: "http://127.0.0.1:8081/fail"
    fallback:
      url: "http://127.0.0.1:8081/success"
YAMLEOF

echo "--- Starting Mock Upstream Server ---"
cat << 'MOCKEOF' > mock_server.go
package main

import "net/http"

func main() {
	http.HandleFunc("/fail", func(w http.ResponseWriter, r *http.Request) { 
		w.WriteHeader(500) 
	})
	http.HandleFunc("/success", func(w http.ResponseWriter, r *http.Request) { 
		w.WriteHeader(200)
		w.Write([]byte("OK_FALLBACK")) 
	})
	http.ListenAndServe(":8081", nil)
}
MOCKEOF

go run mock_server.go &
MOCK_PID=$!

echo "--- Starting AgentMux (Headless) ---"
./agentmux up --headless &
MUX_PID=$!

sleep 2 # Allow servers to start

echo "--- Executing Test Request ---"
RESP=$(curl -s http://localhost:8080/v1/test)

echo "Response received: $RESP"

kill $MUX_PID
kill $MOCK_PID

if [ "$RESP" = "OK_FALLBACK" ]; then
    echo "✅ TEST PASSED: 500 Error correctly triggered fallback response."
    exit 0
else
    echo "❌ TEST FAILED: Fallback was not triggered or response mismatch."
    exit 1
fi
