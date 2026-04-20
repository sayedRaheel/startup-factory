package main

import (
	"fmt"
	"os"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: agentmux [init|up] [--headless]")
		os.Exit(1)
	}

	command := os.Args[1]
	headless := len(os.Args) >= 3 && os.Args[2] == "--headless"

	switch command {
	case "init":
		defaultYaml := `port: 8080
routes:
  - path: "/v1/chat/completions"
    primary:
      url: "https://api.openai.com/v1/chat/completions"
    fallback:
      url: "http://localhost:11434/v1/chat/completions"
`
		err := os.WriteFile("agents.yaml", []byte(defaultYaml), 0644)
		if err != nil {
			fmt.Println("Error writing agents.yaml:", err)
			os.Exit(1)
		}
		fmt.Println("Created agents.yaml. Route configuration ready.")
	case "up":
		config, err := LoadConfig("agents.yaml")
		if err != nil {
			fmt.Println("Failed to load agents.yaml. Run 'agentmux init' first.", err)
			os.Exit(1)
		}

		metrics := &AppMetrics{}

		// Spawn proxy in background
		go StartServer(config, metrics)

		if headless {
			fmt.Printf("Server running in headless mode on port %d\n", config.Port)
			select {} // Block forever
		} else {
			err = RunTUI(metrics)
			if err != nil {
				fmt.Println("TUI Error:", err)
			}
		}
	default:
		fmt.Println("Unknown command:", command)
	}
}
