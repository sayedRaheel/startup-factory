package sandbox

import (
	"fmt"
	"os"
	"os/exec"
	"strings"

	"github.com/agentbox/agentbox/internal/config"
)

type Executor struct {
	Config *config.Config
}

func NewExecutor(cfg *config.Config) *Executor {
	return &Executor{Config: cfg}
}

func (e *Executor) Run(args []string) error {
	if len(args) == 0 {
		return fmt.Errorf("no command provided")
	}

	baseCmd := args[0]

	// 1. Zero-Trust Command Whitelist Check
	allowed := false
	for _, cmd := range e.Config.Whitelist.Commands {
		if baseCmd == cmd {
			allowed = true
			break
		}
	}
	if !allowed {
		return fmt.Errorf("security violation: command '%s' is not in the whitelist", baseCmd)
	}

	// 2. Prepare Sandboxed Execution
	cmd := exec.Command(baseCmd, args[1:]...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin

	// 3. Credential Cloaking & Env Whitelist
	// We ONLY pass explicitly whitelisted environment variables to the child process.
	// The agent receives what it needs, and the rest of the host env is hidden.
	var cleanEnv []string
	for _, envKey := range e.Config.Whitelist.EnvVars {
		if val, exists := os.LookupEnv(envKey); exists {
			cleanEnv = append(cleanEnv, fmt.Sprintf("%s=%s", envKey, val))
		}
	}
	cmd.Env = cleanEnv

	// 4. Execute
	fmt.Printf("[AgentBox] Securing execution for: %s\n", strings.Join(args, " "))
	return cmd.Run()
}
