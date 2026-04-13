package tui

import (
	tea "github.com/charmbracelet/bubbletea"
	"agtop/internal/proxy"
	"agtop/internal/vfs"
)

type interceptMsg proxy.InterceptRequest
type logMsg string
type costMsg proxy.CostUpdate

func waitForIntercept(c chan proxy.InterceptRequest) tea.Cmd {
	return func() tea.Msg {
		return interceptMsg(<-c)
	}
}

func waitForLog(c chan string) tea.Cmd {
	return func() tea.Msg {
		return logMsg(<-c)
	}
}

func waitForCost(c chan proxy.CostUpdate) tea.Cmd {
	return func() tea.Msg {
		return costMsg(<-c)
	}
}

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		return m, nil

	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c", "q":
			return m, tea.Quit
		case " ":
			// Approve intercepted request
			if m.activeReq != nil {
				m.activeReq.Approve <- true
				m.activeReq = nil
				return m, waitForIntercept(m.proxy.InterceptChan)
			}
		case "d":
			// Deny intercepted request
			if m.activeReq != nil {
				m.activeReq.Approve <- false
				m.activeReq = nil
				return m, waitForIntercept(m.proxy.InterceptChan)
			}
		case "r":
			// Trigger deterministic file rollback
			res := vfs.RollbackLatest()
			m.logs = append(m.logs, "[VFS] "+res)
			if len(m.logs) > m.height/2 {
				m.logs = m.logs[len(m.logs)-m.height/2:]
			}
			return m, nil
		}

	case costMsg:
		m.cost += msg.CostDelta
		m.promptTokens += msg.PromptTokens
		m.completionTokens += msg.CompletionTokens
		return m, waitForCost(m.proxy.CostChan)

	case interceptMsg:
		req := proxy.InterceptRequest(msg)
		m.activeReq = &req
		return m, nil

	case logMsg:
		m.logs = append(m.logs, string(msg))
		maxLogs := 15
		if m.height > 10 {
			maxLogs = m.height / 2
		}
		if len(m.logs) > maxLogs {
			m.logs = m.logs[len(m.logs)-maxLogs:] // Ring buffer
		}
		return m, waitForLog(m.runner.LogChan)
	}

	return m, nil
}
