package proxy

import (
	"bytes"
	"crypto/rand"
	"fmt"
	"io"
	"net/http"
	"net/http/httputil"
	"net/url"
)

type InterceptRequest struct {
	ID       string
	Endpoint string
	Body     []byte
	Approve  chan bool
}

type Server struct {
	InterceptChan chan InterceptRequest
	TargetURL     string
	proxy         *httputil.ReverseProxy
}

func NewServer(targetURL string) *Server {
	if targetURL == "" {
		targetURL = "https://api.openai.com"
	}
	target, _ := url.Parse(targetURL)
	
	p := httputil.NewSingleHostReverseProxy(target)
	originalDirector := p.Director
	p.Director = func(req *http.Request) {
		originalDirector(req)
		req.Host = target.Host // Essential for SSL routing to OpenAI/Anthropic
	}

	return &Server{
		InterceptChan: make(chan InterceptRequest),
		TargetURL:     target.String(),
		proxy:         p,
	}
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
		ID:       fmt.Sprintf("req-%x", id),
		Endpoint: r.URL.Path,
		Body:     bodyBytes,
		Approve:  approvalChan,
	}

	approved := <-approvalChan
	if !approved {
		http.Error(w, "Blocked by agtop", http.StatusForbidden)
		return
	}

	s.proxy.ServeHTTP(w, r)
}
