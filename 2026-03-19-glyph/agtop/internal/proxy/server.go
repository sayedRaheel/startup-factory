package proxy

import (
	"bytes"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httputil"
	"net/url"
	"regexp"

	"agtop/internal/vfs"
)

type InterceptRequest struct {
	ID        string
	Direction string // "REQ" or "RES"
	Endpoint  string
	Body      []byte
	Approve   chan bool
}

type CostUpdate struct {
	PromptTokens     int
	CompletionTokens int
	CostDelta        float64
}

type Server struct {
	InterceptChan chan InterceptRequest
	CostChan      chan CostUpdate
	TargetURL     string
	proxy         *httputil.ReverseProxy
}

func NewServer(targetURL string) *Server {
	if targetURL == "" {
		targetURL = "https://api.openai.com"
	}
	target, _ := url.Parse(targetURL)

	interceptChan := make(chan InterceptRequest, 10)
	costChan := make(chan CostUpdate, 100)

	s := &Server{
		InterceptChan: interceptChan,
		CostChan:      costChan,
		TargetURL:     target.String(),
	}

	p := httputil.NewSingleHostReverseProxy(target)
	originalDirector := p.Director
	p.Director = func(req *http.Request) {
		originalDirector(req)
		req.Host = target.Host // Essential for SSL routing to OpenAI/Anthropic
	}

	p.ModifyResponse = func(resp *http.Response) error {
		var bodyBytes []byte
		if resp.Body != nil {
			bodyBytes, _ = io.ReadAll(resp.Body)
			resp.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))
		}

		// Calculate Cost
		var data map[string]interface{}
		if err := json.Unmarshal(bodyBytes, &data); err == nil {
			if usage, ok := data["usage"].(map[string]interface{}); ok {
				var pt, ct float64
				if v, ok := usage["prompt_tokens"].(float64); ok {
					pt = v
				} else if v, ok := usage["input_tokens"].(float64); ok {
					pt = v
				}
				if v, ok := usage["completion_tokens"].(float64); ok {
					ct = v
				} else if v, ok := usage["output_tokens"].(float64); ok {
					ct = v
				}
				
				costDelta := (pt * 0.005 / 1000.0) + (ct * 0.015 / 1000.0) // approx mixed cost
				costChan <- CostUpdate{
					PromptTokens:     int(pt),
					CompletionTokens: int(ct),
					CostDelta:        costDelta,
				}
			}
		}

		// Backup files referenced in tool calls (Regex match heuristic for prototype)
		// Usually tools look like {"name": "write_to_file", "arguments": "{\"path\": \"foo.txt\"}"}
		pathRegex := regexp.MustCompile(`"path"\s*:\s*"([^"]+)"|"file"\s*:\s*"([^"]+)"|"filename"\s*:\s*"([^"]+)"|"command"\s*:\s*"([^"]+)"`)
		matches := pathRegex.FindAllSubmatch(bodyBytes, -1)
		for _, match := range matches {
			for i := 1; i < len(match); i++ {
				if len(match[i]) > 0 {
					val := string(match[i])
					// basic check if it looks like a filename
					if len(val) < 256 && (regexp.MustCompile(`^[\w./-]+$`).MatchString(val)) {
						vfs.Snapshot(val)
					}
				}
			}
		}

		// Intercept the Response (Tool Calls incoming!)
		approvalChan := make(chan bool)
		id := make([]byte, 4)
		rand.Read(id)

		s.InterceptChan <- InterceptRequest{
			ID:        fmt.Sprintf("res-%x", id),
			Direction: "RESPONSE",
			Endpoint:  resp.Request.URL.Path,
			Body:      bodyBytes,
			Approve:   approvalChan,
		}

		approved := <-approvalChan
		if !approved {
			return fmt.Errorf("blocked by agtop user")
		}

		return nil
	}
	s.proxy = p

	return s
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	var bodyBytes []byte
	if r.Body != nil {
		bodyBytes, _ = io.ReadAll(r.Body)
		r.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))
	}

	approvalChan := make(chan bool)
	id := make([]byte, 4)
	rand.Read(id)

	s.InterceptChan <- InterceptRequest{
		ID:        fmt.Sprintf("req-%x", id),
		Direction: "REQUEST",
		Endpoint:  r.URL.Path,
		Body:      bodyBytes,
		Approve:   approvalChan,
	}

	approved := <-approvalChan
	if !approved {
		http.Error(w, "Blocked by agtop", http.StatusForbidden)
		return
	}

	s.proxy.ServeHTTP(w, r)
}
