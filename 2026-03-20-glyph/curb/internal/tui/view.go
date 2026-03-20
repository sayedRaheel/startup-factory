package tui

import (
	"fmt"
	"github.com/charmbracelet/lipgloss"
)

var (
	hudStyle   = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(1).BorderForeground(lipgloss.Color("62"))
	alertStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("196")).Bold(true)
	logStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("240"))
)

func (m ModelState) View() string {
	hud := fmt.Sprintf("🛡️  CURB INTERCEPTOR | Budget: $%.2f / $%.2f\n\n", m.Cost, m.Budget)

	for _, log := range m.Logs {
		hud += logStyle.Render(log) + "\n"
	}

	if m.IsIntercepted {
		hud += "\n" + alertStyle.Render(" CIRCUIT BREAKER TRIPPED! ") + "\n"
		hud += fmt.Sprintf("Reason: %s\n", m.CurrentAlert.Reason)
		hud += fmt.Sprintf("Command: %s\n", m.CurrentAlert.Command)
		hud += "\nAllow execution? [Y/n]"
	}

	return hudStyle.Render(hud)
}
