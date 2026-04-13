package main

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
)

func ExecutePipeline(config *MeshConfig, initialPrompt string) error {
	currentPayload := initialPrompt

	fmt.Printf("🚀 Starting Mesh Pipeline: %s\n\n", config.Name)

	for _, step := range config.Pipeline {
		fmt.Printf("⚙️  Running Agent: [%s]\n", step.Name)

		cmd := exec.Command("sh", "-c", step.Command)

		// Inject environment variables (multiplexing API keys/Hardware targets)
		cmd.Env = os.Environ()
		for k, v := range step.Env {
			cmd.Env = append(cmd.Env, fmt.Sprintf("%s=%s", k, v))
		}

		// Write the previous output (or initial prompt) to this agent's stdin
		cmd.Stdin = bytes.NewBufferString(currentPayload)
		// Pass errors directly to user
		cmd.Stderr = os.Stderr

		output, err := cmd.Output()
		if err != nil {
			return fmt.Errorf("agent [%s] failed: %w", step.Name, err)
		}

		currentPayload = string(output)
	}

	fmt.Printf("\n✅ Pipeline complete. Final Output:\n\n%s\n", currentPayload)
	return nil
}
