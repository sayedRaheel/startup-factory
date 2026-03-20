package tui

import (
	tea "github.com/charmbracelet/bubbletea"
	"github.com/yourorg/curb/internal/engine"
	"github.com/yourorg/curb/internal/proxy"
)

func (m ModelState) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {

	case tea.KeyMsg:
		if m.IsIntercepted {
			switch msg.String() {
			case "y", "Y":
				m.IsIntercepted = false
				m.CurrentAlert.Resume <- true // Tell proxy to continue
				return m, listenForIntercepts(m.Proxy.Intercepts)
			case "n", "N":
				m.CurrentAlert.Resume <- false // Tell proxy to kill process
				return m, tea.Quit
			}
			return m, nil
		}

		// Standard escape hatches
		if msg.String() == "ctrl+c" {
			return m, tea.Quit
		}

	case OutputMsg:
		strMsg := string(msg)
		// Catch completion gracefully
		if strMsg == "EOF_REACHED" {
			return m, tea.Quit
		}

		m.Logs = append(m.Logs, strMsg)
		if len(m.Logs) > 20 { // Keep memory footprint small
			m.Logs = m.Logs[1:]
		}

		cost := engine.ParseCost(strMsg)
		if cost > 0 {
			m.Cost += cost
		}
		return m, listenForOutput(m.Proxy.Output)

	case proxy.InterceptEvent:
		m.IsIntercepted = true
		m.CurrentAlert = msg
		return m, nil // Wait for user Y/N keypress
	}

	return m, nil
}
