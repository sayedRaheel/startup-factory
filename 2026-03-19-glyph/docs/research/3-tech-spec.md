You want to build a pickaxe, not a toy. I respect that. The architecture for `agtop` needs to be aggressively lightweight, highly concurrent, and visually striking. If it takes more than 50 milliseconds to start, or requires installing Node.js, the target audience will rip it apart.

Here is the architectural blueprint, the trade-off matrix, and the execution plan for Forge.

***

### 1. Architectural Decision Record (ADR)

**Decision 1: Language & Runtime**
*   **Choice:** Go (Golang)
*   **Trade-offs:** 
    *   *Pros:* Compiles to a single, zero-dependency statically linked binary. Cross-platform by default. God-tier concurrency primitives (goroutines/channels) which are mandatory for intercepting network traffic while simultaneously rendering a 60fps TUI.
    *   *Cons:* Go’s GUI/TUI ecosystem is less flexible than HTML/CSS. We are locked into terminal cell constraints.
    *   *Mitigation:* Use Charmbracelet to overcome terminal aesthetic limitations.

**Decision 2: TUI Framework**
*   **Choice:** Charmbracelet (`Bubble Tea` + `Lipgloss`)
*   **Trade-offs:** 
    *   *Pros:* The Elm architecture (Model-View-Update) is deterministic. Lipgloss provides CSS-like styling in the terminal. It guarantees the "Hacker News Vibe".
    *   *Cons:* Massive log streams can cause lag if the View function does heavy string concatenation on every tick.
    *   *Mitigation:* We will implement a ring buffer for logs and use the `viewport` component to only render what is visible.

**Decision 3: Interception Mechanism (The Proxy)**
*   **Choice:** Local Reverse Proxy + Environment Variable Injection (`OPENAI_BASE_URL`, `ANTHROPIC_BASE_URL`, `http_proxy`).
*   **Trade-offs:** 
    *   *Pros:* Bypasses the need for users to install custom Root CA certificates for SSL MITM (which is a UX nightmare).
    *   *Cons:* Relies on the target agent respecting standard environment variables for API endpoints or HTTP proxies. If an agent hardcodes `https://api.openai.com` and ignores proxies, we miss it.
    *   *Mitigation:* Most modern agent frameworks (LangChain, CrewAI, AutoGPT) use standard SDKs that respect these env vars.

**Decision 4: State & File Storage**
*   **Choice:** Pure In-Memory State + Local `.agtop/` ephemeral backup directory.
*   **Trade-offs:** 
    *   *Pros:* No SQLite dependency means no CGO, keeping the binary pure Go and compilation instant. Lightning fast.
    *   *Cons:* Metrics are lost when the dashboard closes.
    *   *Mitigation:* Not a problem. `htop` is ephemeral; `agtop` should be too.

***

### 2. Exact Tech Stack & Libraries

*   **Language:** Go 1.22+
*   **TUI Framework:** `github.com/charmbracelet/bubbletea` (State machine)
*   **Styling:** `github.com/charmbracelet/lipgloss` (UI design)
*   **TUI Components:** `github.com/charmbracelet/bubbles` (Viewports, spinners)
*   **Reverse Proxy:** `net/http/httputil` (Go Standard Library - zero external bloat)
*   **Process Management:** `os/exec` (Go Standard Library)

***

### 3. File Structure

```text
agtop/
├── go.mod
├── go.sum
├── main.go                 # Application bootstrap
├── internal/
│   ├── proxy/
│   │   └── server.go       # HTTP reverse proxy & payload inspection
│   ├── runner/
│   │   └── process.go      # Subprocess execution & stdout/stderr pipes
│   ├── tui/
│   │   ├── model.go        # Bubble Tea Model (State)
│   │   ├── update.go       # Bubble Tea Update (Logic/Keys)
│   │   └── view.go         # Bubble Tea View (Render)
│   └── vfs/
│       └── backup.go       # File caching for "Ctrl-Z" rollback
```

***

### 4. Setup Commands for Forge

Run these commands strictly in this order to scaffold the project:

```bash
mkdir agtop && cd agtop
go mod init github.com/yourorg/agtop
go get github.com/charmbracelet/bubbletea
go get github.com/charmbracelet/lipgloss
go get github.com/charmbracelet/bubbles
mkdir -p internal/proxy internal/runner internal/tui internal/vfs
touch main.go internal/proxy/server.go internal/runner/process.go internal/tui/model.go internal/tui/update.go internal/tui/view.go internal/vfs/backup.go
```

***

### 5. Core Implementation (Boilerplate)

#### `main.go`
*The orchestrator. It starts the proxy, spawns the child process with injected env vars, and boots the TUI.*

```go
package main

import (
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/yourorg/agtop/internal/proxy"
	"github.com/yourorg/agtop/internal/runner"
	"github.com/yourorg/agtop/internal/tui"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: agtop <command> [args...]")
		fmt.Println("Example: agtop python agent.go")
		os.Exit(1)
	}

	// 1. Boot the Interception Proxy on a dynamic port
	interceptor := proxy.NewServer()
	go interceptor.Start(":8080") // In prod, bind to port 0 to let OS assign

	// 2. Start the Target Agent Process
	// We inject OPENAI_BASE_URL to route traffic through our proxy
	env := append(os.Environ(), "OPENAI_BASE_URL=http://localhost:8080/v1")
	env = append(env, "ANTHROPIC_BASE_URL=http://localhost:8080/v1")
	
	agentRunner := runner.NewProcess(os.Args[1], os.Args[2:], env)
	go agentRunner.Run()

	// 3. Boot the TUI
	m := tui.InitialModel(interceptor, agentRunner)
	p := tea.NewProgram(m, tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		fmt.Printf("agtop crashed: %v", err)
		os.Exit(1)
	}
}
```

#### `internal/proxy/server.go`
*The gateway. All LLM calls pass through here. We pause requests to wait for TUI approval.*

```go
package proxy

import (
	"bytes"
	"io"
	"net/http"
	"net/http/httputil"
	"net/url"
)

type Server struct {
	// Channels to communicate with the TUI
	InterceptChan chan InterceptRequest
}

type InterceptRequest struct {
	ID       string
	Endpoint string
	Body     []byte
	Approve  chan bool
}

func NewServer() *Server {
	return &Server{
		InterceptChan: make(chan InterceptRequest),
	}
}

func (s *Server) Start(addr string) error {
	// For simplicity in the boilerplate, we hardcode routing to OpenAI.
	// In reality, you'd inspect the request to route to Anthropic/Local etc.
	target, _ := url.Parse("https://api.openai.com")
	
	proxy := httputil.NewSingleHostReverseProxy(target)
	
	// Intercept the request BEFORE sending
	proxy.Director = func(req *http.Request) {
		req.Host = target.Host
		req.URL.Scheme = target.Scheme
		req.URL.Host = target.Host

		// Read body for visualization
		bodyBytes, _ := io.ReadAll(req.Body)
		req.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))

		// Block and ask TUI for permission
		approvalChan := make(chan bool)
		s.InterceptChan <- InterceptRequest{
			ID:       "req-1", // Generate UUID here
			Endpoint: req.URL.Path,
			Body:     bodyBytes,
			Approve:  approvalChan,
		}

		approved := <-approvalChan
		if !approved {
			// If denied, we should technically return a 403 or a mock response,
			// but for this snippet we drop it or mock it.
			req.URL = nil 
		}
	}

	return http.ListenAndServe(addr, proxy)
}
```

#### `internal/tui/model.go` & `internal/tui/update.go`
*The dashboard state machine. Handles Space to approve/deny and R to rollback.*

```go
// internal/tui/model.go
package tui

import (
	tea "github.com/charmbracelet/bubbletea"
	"github.com/yourorg/agtop/internal/proxy"
	"github.com/yourorg/agtop/internal/runner"
)

type Model struct {
	proxy       *proxy.Server
	runner      *runner.Process
	activeReq   *proxy.InterceptRequest
	cost        float64
	logs        []string
}

func InitialModel(p *proxy.Server, r *runner.Process) Model {
	return Model{
		proxy:  p,
		runner: r,
		cost:   0.00,
	}
}

func (m Model) Init() tea.Cmd {
	return waitForIntercept(m.proxy.InterceptChan)
}

// internal/tui/update.go
type interceptMsg proxy.InterceptRequest

func waitForIntercept(c chan proxy.InterceptRequest) tea.Cmd {
	return func() tea.Msg {
		return interceptMsg(<-c)
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
			// vfs.RollbackLatest()
			m.logs = append(m.logs, "Rolled back last file modification.")
		}

	case interceptMsg:
		req := proxy.InterceptRequest(msg)
		m.activeReq = &req
		return m, nil
	}
	return m, nil
}
```

#### `internal/tui/view.go`
*The ruthless aesthetic rendering.*

```go
package tui

import (
	"fmt"
	"github.com/charmbracelet/lipgloss"
)

var (
	titleStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#FAFAFA")).Background(lipgloss.Color("#7D56F4")).Padding(0, 1)
	warnStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("#FF5F87")).Bold(true)
	infoStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("#00D787"))
)

func (m Model) View() string {
	s := titleStyle.Render(" agtop ") + fmt.Sprintf(" - Total Token Cost: $%.4f\n\n", m.cost)

	if m.activeReq != nil {
		s += warnStyle.Render("⚠️ INTERCEPTED API CALL ⚠️") + "\n"
		s += fmt.Sprintf("Endpoint: %s\n", m.activeReq.Endpoint)
		// Truncate body for display
		bodyStr := string(m.activeReq.Body)
		if len(bodyStr) > 100 {
			bodyStr = bodyStr[:100] + "..."
		}
		s += fmt.Sprintf("Payload: %s\n\n", bodyStr)
		s += "[SPACE] to Approve | [D] to Deny\n"
	} else {
		s += infoStyle.Render("Agent running... Monitoring network and filesystem.") + "\n"
	}

	s += "\n--- Logs ---\n"
	for _, l := range m.logs {
		s += l + "\n"
	}

	s += "\n[Q]uit | [R]ollback FS\n"
	return s
}
```

***

### Handing off to Forge
The bones are here. The trade-offs are calculated. The UX is defined. Tell Forge to execute the setup commands, implement the boilerplate, and wire up the Subprocess standard output streams to feed into the Bubble Tea `Model.logs` array via `tea.Cmd`. 

Build the pickaxe.
