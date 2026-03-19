package tui

import (
	tea "github.com/charmbracelet/bubbletea"
	"agtop/internal/proxy"
	"agtop/internal/vfs"
)

type interceptMsg proxy.InterceptRequest
type logMsg string

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

func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {

	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c", "q":
			return m, tea.Quit
		case " ":
			// Approve intercepted request
			if m.activeReq != nil {
				m.activeReq.Approve <- true
				m.cost += 0.02 // Mock cost increment
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
			m.logs = append(m.logs, res)
			if len(m.logs) > 15 {
				m.logs = m.logs[len(m.logs)-15:]
			}
			return m, nil
		}

	case interceptMsg:
		req := proxy.InterceptRequest(msg)
		m.activeReq = &req
		return m, nil

	case logMsg:
		m.logs = append(m.logs, string(msg))
		if len(m.logs) > 15 {
			m.logs = m.logs[len(m.logs)-15:] // Ring buffer
		}
		return m, waitForLog(m.runner.LogChan)
	}

	return m, nil
}
