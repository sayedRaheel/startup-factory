package main

import (
	"bytes"
	"fmt"
	"io"
	"net/http"
)

func StartServer(config *Config, metrics *AppMetrics) {
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		metrics.IncReq()

		var matchedRoute *Route
		for _, route := range config.Routes {
			if route.Path == r.URL.Path {
				matchedRoute = &route
				break
			}
		}

		if matchedRoute == nil {
			http.Error(w, "Route not found", http.StatusNotFound)
			return
		}

		bodyBytes, err := io.ReadAll(r.Body)
		if err != nil {
			http.Error(w, "Bad request", http.StatusBadRequest)
			return
		}

		client := &http.Client{}

		doReq := func(targetUrl string) (*http.Response, error) {
			req, err := http.NewRequest(r.Method, targetUrl, bytes.NewReader(bodyBytes))
			if err != nil {
				return nil, err
			}
			for k, vv := range r.Header {
				for _, v := range vv {
					req.Header.Add(k, v)
				}
			}
			return client.Do(req)
		}

		resp, err := doReq(matchedRoute.Primary.URL)

		if err != nil || resp.StatusCode >= 500 || resp.StatusCode == 429 {
			if matchedRoute.Fallback != nil {
				metrics.IncFallback()
				if resp != nil {
					resp.Body.Close()
				}
				resp, err = doReq(matchedRoute.Fallback.URL)
			}
		}

		if err != nil {
			http.Error(w, "Bad Gateway", http.StatusBadGateway)
			return
		}
		defer resp.Body.Close()

		for k, vv := range resp.Header {
			for _, v := range vv {
				w.Header().Add(k, v)
			}
		}
		w.WriteHeader(resp.StatusCode)

		// Manual stream copy with flushing for SSE support
		flusher, canFlush := w.(http.Flusher)
		buf := make([]byte, 4096)
		for {
			n, err := resp.Body.Read(buf)
			if n > 0 {
				w.Write(buf[:n])
				if canFlush {
					flusher.Flush()
				}
			}
			if err != nil {
				break
			}
		}
	})

	addr := fmt.Sprintf(":%d", config.Port)
	http.ListenAndServe(addr, nil)
}
