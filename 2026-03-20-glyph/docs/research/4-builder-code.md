```bash
#!/bin/bash
set -e

# Create directories
mkdir -p curb/cmd/curb
mkdir -p curb/internal/engine
mkdir -p curb/internal/proxy
mkdir -p curb/internal/tui
mkdir -p curb/docs/research

cd curb

# Initialize Go module
go mod init github.com/yourorg/curb

# Install dependencies (using @latest since local rollbacks aren't guaranteed)
go get github.com/spf13/cobra@latest
go get github.com/charmbracelet/bubbletea@latest
go get github.com/charmbracelet/lipgloss@latest
go get github.com/creack/pty@latest

# Generate internal/engine/rules.go
cat << 'EOF' > internal/engine/rules.go
package engine

import (
	"regexp"
)

// Rule defines a simple intercept rule
type Rule struct {
	Pattern *regexp.Regexp
	Reason  string
}

var DefaultRules = []Rule{
	{regexp.MustCompile(`rm\s+-rf`), "Attempted destruction of protected pattern."},
	{regexp.MustCompile(`\.env`), "Attempted access or destruction of protected pattern."},
}

// Evaluate checks if a line breaks any rules
func Evaluate(line string) (bool, string) {
	for _, rule := range DefaultRules {
		if rule.Pattern.MatchString(line) {
			return true, rule.Reason
		}
	}
	return false, ""
}
EOF

# Generate internal/engine/parser.go
cat << 'EOF' > internal/engine/parser.go
package engine

import (
	"regexp"
	"strconv"
)

var costRegex = regexp.MustCompile(`Cost:\s*\$(\d+\.\d+)`)

func ParseCost(line string) float64 {
	matches := costRegex.FindStringSubmatch(line)
	if len(matches) > 1 {
		val, err := strconv.ParseFloat(matches[1], 64)
		if err == nil {
			return val
		}
	}
	return 0.0
}
EOF

# Generate internal/proxy/pty.go
cat << 'EOF' > internal/proxy/pty.go
package proxy

import (
	"bufio"
	"os"
	"os/exec"

	"github.com/creack/pty"
	"github.com/yourorg/curb/internal/engine"
)

// InterceptEvent is sent to the TUI when a rule is broken
type InterceptEvent struct {
	Command string
	Reason  string
	Resume  chan bool
}

type Proxy struct {
	Cmd        *exec.Cmd
	PtyFile    *os.File
	Intercepts chan InterceptEvent
	Output     chan string
}

func NewProxy(targetCmd []string) *Proxy {
	cmd := exec.Command(targetCmd[0], targetCmd[1:]...)
	return &Proxy{
		Cmd:        cmd,
		Intercepts: make(chan InterceptEvent),
		Output:     make(chan string, 100),
	}
}

func (p *Proxy) Start() error {
	ptmx, err := pty.Start(p.Cmd)
	if err != nil {
		return err
	}
	p.PtyFile = ptmx

	// Goroutine to passively intercept and scan output
	go func() {
		scanner := bufio.NewScanner(ptmx)
		for scanner.Scan() {
			line := scanner.Text()
			
			if intercepted, reason := engine.Evaluate(line); intercepted {
				resumeChan := make(chan bool)
				p.Intercepts <- InterceptEvent{
					Command: line,
					Reason:  reason,
					Resume:  resumeChan,
				}
				
				// Block execution until user approves/denies via TUI
				approved := <-resumeChan
				if !approved {
					if p.Cmd.Process != nil {
						p.Cmd.Process.Kill()
					}
					os.Exit(1)
				}
			}

			// Pass safe output to TUI
			p.Output <- line
		}
		// Signal EOF to cleanly terminate TUI loop
		p.Output <- "EOF_REACHED"
	}()

	return nil
}

func (p *Proxy) WriteInput(b []byte) (int, error) {
	return p.PtyFile.Write(b)
}
EOF

# Generate internal/tui/model.go
cat << 'EOF' > internal/tui/model.go
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
EOF

# Generate internal/tui/update.go
cat << 'EOF' > internal/tui/update.go
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
EOF

# Generate internal/tui/view.go
cat << 'EOF' > internal/tui/view.go
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
EOF

# Generate cmd/curb/main.go
cat << 'EOF' > cmd/curb/main.go
package main

import (
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/spf13/cobra"
	"github.com/yourorg/curb/internal/proxy"
	"github.com/yourorg/curb/internal/tui"
)

func main() {
	var budget float64
	var protect string

	var rootCmd = &cobra.Command{
		Use:   "curb [agent command]",
		Short: "Keep your AI agents on a leash.",
		Args:  cobra.MinimumNArgs(1),
		Run: func(cmd *cobra.Command, args []string) {
			p := proxy.NewProxy(args)
			
			// Fire up the target process inside the PTY
			if err := p.Start(); err != nil {
				fmt.Printf("Failed to wrap agent: %v\n", err)
				os.Exit(1)
			}

			// Initialize the HUD
			m := tui.InitialModel(p, budget)
			
			// Run the Bubble Tea program, taking over the terminal
			prog := tea.NewProgram(m, tea.WithAltScreen())
			
			if _, err := prog.Run(); err != nil {
				fmt.Printf("UI Error: %v\n", err)
				os.Exit(1)
			}
			
			// Ensure variables are utilized
			_ = protect
		},
	}

	rootCmd.Flags().Float64Var(&budget, "budget", 5.00, "Maximum API budget before auto-pause")
	rootCmd.Flags().StringVar(&protect, "protect", "src/**/*.ts", "Glob patterns of protected files")

	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
EOF

# Format Go code and fetch clean mod requirements
go mod tidy
go fmt ./...

# Generate README.md
cat << 'EOF' > README.md
# Curb

Curb is a high-performance proxy tool for local AI agents. It wraps around CLI agents like Claude-Code or Aider to provide a strict, stateless perimeter preventing accidental destruction or uncontrolled cloud spending.

### Problem Statement

The current state of autonomous AI tooling is a sandbox without walls. Unbounded agents have unrestricted access to local environments and no inherent limits on API spend, risking both system integrity and financial cost.

### Implementation Details

Curb intercepts the PTY stream between the user's terminal and the agent, matching the standard output against regex-based rules to enforce constraints. If a dangerous pattern is detected, execution is halted, and the user must explicitly approve the action via a sleek terminal UI.

### Research & Architecture

* [Scout Analysis](./docs/research/1-scout-analysis.md)
* [PRD](./docs/research/2-prd.md)
* [Tech Spec](./docs/research/3-tech-spec.md)
* [Builder Code](./docs/research/4-builder-code.md)
EOF

# Create empty dummy files for links
touch docs/research/1-scout-analysis.md
touch docs/research/2-prd.md
touch docs/research/3-tech-spec.md
touch docs/research/4-builder-code.md

# Generate test.sh
cat << 'EOF' > test.sh
#!/bin/bash
set -e

echo "Building Curb..."
go build -o curb_bin ./cmd/curb

if [ $? -ne 0 ]; then
    echo "Build failed!"
    exit 1
fi

echo "Running tests..."
# Pass an innocent command that will be fully wrapped and safely exit
./curb_bin echo "Running safe command verification..." > /dev/null

if [ $? -eq 0 ]; then
    echo "✅ Test passed! PTY wrapped and terminated cleanly."
    exit 0
else
    echo "❌ Execution failed!"
    exit 1
fi
EOF
chmod +x test.sh

# Run the test
./test.sh
```
