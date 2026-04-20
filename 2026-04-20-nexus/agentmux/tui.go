package main

import (
	"fmt"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type tickMsg time.Time

type model struct {
	metrics *AppMetrics
}

func (m model) Init() tea.Cmd {
	return tea.Tick(time.Millisecond*100, func(t time.Time) tea.Msg {
		return tickMsg(t)
	})
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		if msg.String() == "q" || msg.String() == "ctrl+c" {
			return m, tea.Quit
		}
	case tickMsg:
		return m, tea.Tick(time.Millisecond*100, func(t time.Time) tea.Msg {
			return tickMsg(t)
		})
	}
	return m, nil
}

var borderStyle = lipgloss.NewStyle().
	Border(lipgloss.RoundedBorder()).
	Padding(1, 2)

func (m model) View() string {
	reqs := m.metrics.TotalRequests.Load()
	falls := m.metrics.FallbacksTriggered.Load()

	content := fmt.Sprintf("AgentMux Live Traffic\n\nTotal Requests: %d\nFallbacks Triggered: %d\n\nPress 'q' to quit", reqs, falls)
	return borderStyle.Render(content)
}

func RunTUI(metrics *AppMetrics) error {
	p := tea.NewProgram(model{metrics: metrics}, tea.WithAltScreen())
	_, err := p.Run()
	return err
}
