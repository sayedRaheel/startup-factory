package main

import (
	"fmt"
	"net"
	"net/http"
	"os"

	tea "github.com/charmbracelet/bubbletea"
	"agtop/internal/proxy"
	"agtop/internal/runner"
	"agtop/internal/tui"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: agtop <command> [args...]")
		fmt.Println("Example: agtop python agent.py")
		os.Exit(1)
	}

	// 1. Boot the Interception Proxy on a dynamic OS-assigned port
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		fmt.Printf("Failed to bind proxy port: %v\n", err)
		os.Exit(1)
	}
	port := listener.Addr().(*net.TCPAddr).Port
	proxyURL := fmt.Sprintf("http://127.0.0.1:%d", port)

	interceptor := proxy.NewServer("") // Default routes to OpenAI
	go http.Serve(listener, interceptor)

	// 2. Start the Target Agent Process with injected Environment Variables
	env := os.Environ()
	env = append(env, "OPENAI_BASE_URL="+proxyURL+"/v1")
	env = append(env, "ANTHROPIC_BASE_URL="+proxyURL+"/v1")
	env = append(env, "http_proxy="+proxyURL) // Catch generic HTTP agents

	agentRunner := runner.NewProcess(os.Args[1], os.Args[2:], env)
	go agentRunner.Run()

	// 3. Boot the TUI
	m := tui.InitialModel(interceptor, agentRunner)
	p := tea.NewProgram(m, tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		fmt.Printf("agtop crashed: %v\n", err)
		os.Exit(1)
	}
}
