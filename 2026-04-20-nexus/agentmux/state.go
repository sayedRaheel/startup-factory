package main

import "sync/atomic"

type AppMetrics struct {
	TotalRequests      atomic.Uint64
	ActiveConnections  atomic.Uint64
	FallbacksTriggered atomic.Uint64
	BytesTransferred   atomic.Uint64
}

func (m *AppMetrics) IncReq() {
	m.TotalRequests.Add(1)
}

func (m *AppMetrics) IncFallback() {
	m.FallbacksTriggered.Add(1)
}
