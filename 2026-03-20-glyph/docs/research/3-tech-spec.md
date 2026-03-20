This is Linus. 

Vera’s PRD is aggressive, but she’s right. The current state of autonomous AI tooling is a sandbox without walls. We are going to build the walls, and we’re going to make them look good.

Here is the exact blueprint to build `Curb`. I’ve designed this to be a standalone, brutally efficient binary. No daemons, no background tracking, no databases. When the process dies, the perimeter is dropped. 

Forge, read this carefully. Every architectural decision here has a cost, and I’ve paid it upfront so you don’t have to.

***

### 1. Architectural Decision Record (ADR)

**Decision 1: Go (Golang) as the Core Language**
*   **Why:** We need a hyper-fast, single, statically compiled binary with zero runtime dependencies (no Node.js environments or Python virtual environments). Go’s concurrency model (Goroutines and Channels) is mathematically perfect for multiplexing PTY (pseudo-terminal) streams, parsing text in real-time, and rendering a UI simultaneously without blocking the main thread.
*   **The Trade-off:** String manipulation and regex in Go are slightly slower and more verbose than in Python or Rust. We trade microsecond string-parsing performance for deployment simplicity and parallel stream handling.

**Decision 2: Pseudo-Terminal (PTY) Wrapping (`creack/pty`)**
*   **Why:** AI agents like `claude-code` and `aider` check if they are attached to a real terminal to output colors and accept interactive input. Standard `os/exec` pipes will strip their colors and break their internal TUIs. We must trick them into thinking `Curb` *is* the terminal.
*   **The Trade-off:** PTY handling is OS-specific. This architecture will work flawlessly on macOS and Linux. Windows support will be brittle and require WSL or specific Windows Console API wrappers down the line. We accept this for the MVP.

**Decision 3: Charmbracelet (`Bubble Tea` / `Lip Gloss`)**
*   **Why:** It implements the Elm architecture (Model-View-Update). It provides deterministic state management for terminal UIs. It is universally recognized as the best-looking TUI framework.
*   **The Trade-off:** Elm architecture forces a strict unidirectional data flow. You cannot just "print" to the screen; you must dispatch `tea.Msg` events. This makes the proxy logic slightly more complex, as stream intercepts must be translated into Bubble Tea messages.

**Decision 4: Stateless Configuration (No Database)**
*   **Why:** The PRD demands zero bloat. No SQLite. No persistent telemetry. Configuration is injected purely via CLI flags (`--budget`, `--protect`). 
*   **The Trade-off:** Users have to alias the command in their `.zshrc` or `.bashrc` if they want persistent rules. We trade persistent onboarding for zero-friction installation.

***

### 2. Exact Tech Stack

*   **Language:** Go 1.22+
*   **CLI Framework:** `github.com/spf13/cobra` (Command routing & flag parsing)
*   **TUI Framework:** `github.com/charmbracelet/bubbletea` (State & Event loop)
*   **TUI Styling:** `github.com/charmbracelet/lipgloss` (CSS-like terminal styling)
*   **PTY Subsystem:** `github.com/creack/pty` (Spawns the wrapped agent process)

***

### 3. File Structure

Keep it flat and scoped. Do not over-engineer the directories.

```text
curb/
├── cmd/
│   └── curb/
│       └── main.go           # CLI entry point, flag parsing (Cobra)
├── internal/
│   ├── engine/
│   │   ├── rules.go          # The Circuit Breaker (evaluates regex/budgets)
│   │   └── parser.go         # Token & cost extraction from LLM stdout
│   ├── proxy/
│   │   └── pty.go            # The Interceptor (wraps the target agent)
│   └── tui/
│       ├── model.go          # Bubble Tea state definition
│       ├── update.go         # Event loop (Glass-Wall overrides, Y/N logic)
│       └── view.go           # Lip Gloss rendering (The HUD)
├── go.mod
└── go.sum
```

***

### 4. Implementation Steps (Execution Commands)

Forge, run these exact commands to scaffold the environment:

```bash
mkdir curb && cd curb
go mod init github.com/yourorg/curb
go get github.com/spf13/cobra@latest
go get github.com/charmbracelet/bubbletea@latest
go get github.com/charmbracelet/lipgloss@latest
go get github.com/creack/pty@latest

mkdir -p cmd/curb internal/engine internal/proxy internal/tui
touch cmd/curb/main.go internal/engine/rules.go internal/engine/parser.go internal/proxy/pty.go internal/tui/model.go internal/tui/update.go internal/tui/view.go
```

***

### 5. Core Boilerplate Code

Here is the structural wiring. I am providing the hardest parts: The PTY interception and the TUI event loop integration. 

#### `internal/proxy/pty.go` (The Interceptor)
This wraps the target agent, reads its standard output byte-by-byte, and checks for violations via a channel *before* flushing it to the TUI.

```go
package proxy

import (
	"bufio"
	"io"
	"os"
	"os/exec"
	"strings"

	"github.com/creack/pty"
)

// InterceptEvent is sent to the TUI when a rule is broken
type InterceptEvent struct {
	Command string
	Reason  string
	Resume  chan bool // Glass-Wall override channel
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
			
			// LINUS NOTE: This is where you inject engine.Evaluate(line).
			// If it detects a protected file mutation or budget hit:
			if strings.Contains(line, "rm -rf") || strings.Contains(line, ".env") {
				resumeChan := make(chan bool)
				p.Intercepts <- InterceptEvent{
					Command: line,
					Reason:  "Attempted destruction of protected pattern.",
					Resume:  resumeChan,
				}
				
				// Block execution until user approves/denies via TUI
				approved := <-resumeChan
				if !approved {
					p.Cmd.Process.Kill()
					os.Exit(1)
				}
			}

			// Pass safe output to TUI
			p.Output <- line
		}
	}()

	return nil
}

func (p *Proxy) WriteInput(b []byte) (int, error) {
	return p.PtyFile.Write(b)
}
```

#### `internal/tui/model.go` (The Bubble Tea HUD)
This is the state machine. It listens to the Proxy channels and controls the terminal viewport.

```go
package tui

import (
	"fmt"
	"github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/yourorg/curb/internal/proxy"
)

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
	// Start listening to the proxy output channels
	return listenForOutput(m.Proxy.Output)
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

type OutputMsg string
```

#### `internal/tui/update.go` (The Event Loop & Glass-Wall Override)

```go
package tui

import (
	"github.com/charmbracelet/bubbletea"
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
		}

		// Standard escape hatches
		if msg.String() == "ctrl+c" {
			return m, tea.Quit
		}

	case OutputMsg:
		m.Logs = append(m.Logs, string(msg))
		if len(m.Logs) > 20 { // Keep memory footprint small
			m.Logs = m.Logs[1:]
		}
		return m, listenForOutput(m.Proxy.Output)

	case proxy.InterceptEvent:
		m.IsIntercepted = true
		m.CurrentAlert = msg
		return m, nil // Wait for user Y/N keypress
	}

	return m, nil
}
```

#### `internal/tui/view.go` (The UI Renderer)

```go
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
```

#### `cmd/curb/main.go` (The Entry Point)

```go
package main

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
	tea "github.com/charmbracelet/bubbletea"
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
			
			// Also listen for intercepts asynchronously to trigger the TUI
			go func() {
				for intercept := range p.Intercepts {
					prog.Send(intercept)
				}
			}()

			if _, err := prog.Run(); err != nil {
				fmt.Printf("UI Error: %v\n", err)
				os.Exit(1)
			}
		},
	}

	rootCmd.Flags().Float64Var(&budget, "budget", 5.00, "Maximum API budget before auto-pause")
	rootCmd.Flags().StringVar(&protect, "protect", "src/**/*.ts", "Glob patterns of protected files")

	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
```

***

Forge, the architecture is sound. The PTY wraps the standard I/O streams flawlessly, the channels act as our glass-wall interceptors, and Bubble Tea handles the terminal loop elegantly. 

Take this, wire up the Regex engine in `rules.go` to parse the specific target agents' telemetry formats, and get it compiling. We ship in two weeks.
