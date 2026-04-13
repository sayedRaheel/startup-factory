package tui

import (
	tea "github.com/charmbracelet/bubbletea"
	"agtop/internal/proxy"
	"agtop/internal/runner"
)

type Model struct {
	proxy       *proxy.Server
	runner      *runner.Process
	activeReq   *proxy.InterceptRequest
	cost        float64
	promptTokens int
	completionTokens int
	logs        []string
	width       int
	height      int
}

func InitialModel(p *proxy.Server, r *runner.Process) Model {
	return Model{
		proxy:  p,
		runner: r,
		cost:   0.00,
		logs:   make([]string, 0),
	}
}

func (m Model) Init() tea.Cmd {
	return tea.Batch(
		waitForIntercept(m.proxy.InterceptChan),
		waitForCost(m.proxy.CostChan),
		waitForLog(m.runner.LogChan),
	)
}
