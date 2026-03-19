package proxy

import (
	"bytes"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestProxy(t *testing.T) {
	// Mock upstream target server
	target := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	}))
	defer target.Close()

	// Setup our interception proxy
	p := NewServer(target.URL)
	proxySrv := httptest.NewServer(p)
	defer proxySrv.Close()

	// Background routine to automatically approve the intercepted request
	go func() {
		select {
		case req := <-p.InterceptChan:
			req.Approve <- true
		case <-time.After(2 * time.Second):
			t.Error("Timeout waiting for interception request")
		}
	}()

	// Send test request through proxy
	resp, err := http.Post(proxySrv.URL+"/v1/chat/completions", "application/json", bytes.NewBufferString(`{"prompt":"test"}`))
	if err != nil {
		t.Fatalf("Failed to execute request: %v", err)
	}
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("Expected status 200 OK, got %d", resp.StatusCode)
	}
}
