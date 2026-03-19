package tui

import (
	"fmt"
	"github.com/charmbracelet/lipgloss"
)

var (
	titleStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#FAFAFA")).Background(lipgloss.Color("#7D56F4")).Padding(0, 1)
	warnStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("#FF5F87")).Bold(true)
	infoStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("#00D787"))
	logStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("#8A8A8A"))
)

func (m Model) View() string {
	s := titleStyle.Render(" agtop ") + fmt.Sprintf(" - Total Token Cost: $%.4f\n\n", m.cost)

	if m.activeReq != nil {
		s += warnStyle.Render("⚠️ INTERCEPTED API CALL ⚠️") + "\n"
		s += fmt.Sprintf("Endpoint: %s\n", m.activeReq.Endpoint)
		
		bodyStr := string(m.activeReq.Body)
		if len(bodyStr) > 200 {
			bodyStr = bodyStr[:200] + "..."
		}
		s += fmt.Sprintf("Payload: %s\n\n", bodyStr)
		s += "[SPACE] to Approve | [D] to Deny\n"
	} else {
		s += infoStyle.Render("Agent running... Monitoring network and filesystem.") + "\n"
	}

	s += "\n--- Subprocess Logs ---\n"
	for _, l := range m.logs {
		s += logStyle.Render(l) + "\n"
	}

	s += "\n[Q]uit | [R]ollback FS\n"
	return s
}
