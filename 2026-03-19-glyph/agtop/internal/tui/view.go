package tui

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

var (
	baseStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("252"))

	titleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color("#000000")).
			Background(lipgloss.Color("#00FF00")).
			Padding(0, 1)

	headerStyle = lipgloss.NewStyle().
			BorderStyle(lipgloss.NormalBorder()).
			BorderBottom(true).
			BorderForeground(lipgloss.Color("240"))

	panelStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("62")).
			Padding(0, 1)

	warnStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#FF5F87")).
			Bold(true).
			Blink(true)

	infoStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#00D787"))

	logStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("#8A8A8A"))

	keyStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("205")).
			Bold(true)

	boldStyle = lipgloss.NewStyle().Bold(true)
)

func progressBar(percent float64, width int, color string) string {
	fill := int(float64(width) * percent)
	if fill > width {
		fill = width
	}
	if fill < 0 {
		fill = 0
	}
	
	filled := strings.Repeat("█", fill)
	empty := strings.Repeat("░", width-fill)
	
	barStyle := lipgloss.NewStyle().Foreground(lipgloss.Color(color))
	return barStyle.Render(fmt.Sprintf("[%s%s]", filled, empty)) + fmt.Sprintf(" %3.0f%%", percent*100)
}

func formatJSON(data []byte) string {
	var obj map[string]interface{}
	if err := json.Unmarshal(data, &obj); err != nil {
		s := string(data)
		if len(s) > 1000 {
			return s[:1000] + "...\n(Truncated)"
		}
		return s
	}
	b, _ := json.MarshalIndent(obj, "", "  ")
	s := string(b)
	if len(s) > 1000 {
		return s[:1000] + "\n... (Truncated)"
	}
	return s
}

func (m Model) View() string {
	if m.width == 0 {
		return "Booting agtop telemetry dashboard..."
	}

	// Top Header
	title := titleStyle.Render(" agtop ")
	
	// Assuming 128k context window max for UI purposes
	ctxPercent := float64(m.promptTokens+m.completionTokens) / 128000.0
	if ctxPercent > 1.0 { ctxPercent = 1.0 }

	ctxBar := "Ctx " + progressBar(ctxPercent, 20, "#5F87FF")
	stats := fmt.Sprintf("Cost: $%.4f  |  Tokens: %d In / %d Out", m.cost, m.promptTokens, m.completionTokens)
	
	headerContent := lipgloss.JoinHorizontal(lipgloss.Top,
		title,
		"  ",
		ctxBar,
		"    ",
		stats,
	)
	
	header := headerStyle.Width(m.width).Render(headerContent)

	// Middle section: Logs (Left) and Intercept (Right)
	panelWidth := m.width / 2
	if panelWidth < 30 {
		panelWidth = 30
	}

	panelHeight := m.height - lipgloss.Height(header) - 3 // Space for header and footer
	if panelHeight < 10 {
		panelHeight = 10
	}

	// Logs Panel
	logsStr := boldStyle.Render("Subprocess Logs") + "\n\n"
	for _, l := range m.logs {
		if strings.Contains(l, "[ERR]") {
			logsStr += lipgloss.NewStyle().Foreground(lipgloss.Color("196")).Render(l) + "\n"
		} else if strings.Contains(l, "[VFS]") {
			logsStr += lipgloss.NewStyle().Foreground(lipgloss.Color("220")).Render(l) + "\n"
		} else {
			logsStr += logStyle.Render(l) + "\n"
		}
	}
	leftPanel := panelStyle.Width(panelWidth - 2).Height(panelHeight).Render(logsStr)

	// Intercept Panel
	rightContent := boldStyle.Render("Agent Stream") + "\n\n"
	if m.activeReq != nil {
		rightContent += warnStyle.Render("⚠️ INTERCEPTED EVENT ⚠️") + "\n\n"
		rightContent += fmt.Sprintf("%s %s\n", boldStyle.Render("Direction:"), m.activeReq.Direction)
		rightContent += fmt.Sprintf("%s %s\n", boldStyle.Render("Endpoint: "), m.activeReq.Endpoint)
		
		bodyStr := formatJSON(m.activeReq.Body)
		rightContent += fmt.Sprintf("\n%s\n%s\n\n", boldStyle.Render("Payload:"), logStyle.Render(bodyStr))
		
		rightContent += keyStyle.Render("[SPACE]") + " Approve  |  " + keyStyle.Render("[D]") + " Deny\n"
	} else {
		rightContent += infoStyle.Render("✓ Agent running autonomously.") + "\n"
		rightContent += infoStyle.Render("Monitoring network, LLM tool calls, and VFS.") + "\n"
	}
	
	borderColor := lipgloss.Color("62")
	if m.activeReq != nil {
		borderColor = lipgloss.Color("205") // Pink border when intercepted
	}
	
	rightPanel := panelStyle.Width(panelWidth - 2).Height(panelHeight).BorderForeground(borderColor).Render(rightContent)

	middle := lipgloss.JoinHorizontal(lipgloss.Top, leftPanel, rightPanel)

	// Footer
	footer := "\n " + keyStyle.Render("[Q]") + " Quit  |  " + keyStyle.Render("[R]") + " Rollback Last Mod (VFS) "
	
	return baseStyle.Render(lipgloss.JoinVertical(lipgloss.Left, header, middle, footer))
}
