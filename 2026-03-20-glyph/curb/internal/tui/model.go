package tui

import (
	tea "github.com/charmbracelet/bubbletea"
	"github.com/yourorg/curb/internal/proxy"
)

type OutputMsg string

type ModelState struct {
	Proxy         *proxy.Proxy
	Logs          []string
	Budget        float64
	Cost          float64
	IsIntercepted bool
	CurrentAlert  proxy.InterceptEvent
}

func InitialModel(p *proxy.Proxy, budget float64) ModelState {
	return ModelState{
		Proxy:  p,
		Budget: budget,
		Cost:   0.00,
	}
}

func (m ModelState) Init() tea.Cmd {
	// Start listening to both output and intercepts
	return tea.Batch(
		listenForOutput(m.Proxy.Output),
		listenForIntercepts(m.Proxy.Intercepts),
	)
}

// listenForOutput converts channel reads into Bubble Tea messages
func listenForOutput(sub chan string) tea.Cmd {
	return func() tea.Msg {
		return OutputMsg(<-sub)
	}
}

// listenForIntercepts catches Circuit Breaker triggers
func listenForIntercepts(sub chan proxy.InterceptEvent) tea.Cmd {
	return func() tea.Msg {
		return <-sub
	}
}
