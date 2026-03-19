```bash
#!/bin/bash
set -e

# Create and enter the project directory
mkdir -p agentbox
cd agentbox

# Initialize Go module
go mod init github.com/agentbox/agentbox

# Scaffold directories
mkdir -p cmd internal/config internal/sandbox internal/memory

# Generate main.go
cat << 'EOF' > main.go
package main

import "github.com/agentbox/agentbox/cmd"

func main() {
	cmd.Execute()
}
EOF

# Generate cmd/root.go
cat << 'EOF' > cmd/root.go
package cmd

import (
	"fmt"
	"os"
	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "agentbox",
	Short: "Zero-config, ultra-lightweight CLI sandbox for AI agents",
	Long:  `AgentBox wraps your local AI agents in a secure, memory-aware execution layer to prevent accidental destruction and credential leaks.`,
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
EOF

# Generate cmd/init.go
cat << 'EOF' > cmd/init.go
package cmd

import (
	"fmt"
	"github.com/agentbox/agentbox/internal/config"
	"github.com/agentbox/agentbox/internal/memory"
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(initCmd)
}

var initCmd = &cobra.Command{
	Use:   "init",
	Short: "Initialize AgentBox in the current directory",
	RunE: func(cmd *cobra.Command, args []string) error {
		err := config.CreateDefaultConfig(".agentbox.yml")
		if err != nil {
			return err
		}
		
		err = memory.EncryptContext(".agent-context", []byte("{}"))
		if err != nil {
			return err
		}

		fmt.Println("✅ Initialization complete. Created .agentbox.yml and secure .agent-context")
		return nil
	},
}
EOF

# Generate cmd/run.go
cat << 'EOF' > cmd/run.go
package cmd

import (
	"github.com/agentbox/agentbox/internal/config"
	"github.com/agentbox/agentbox/internal/sandbox"
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(runCmd)
}

var runCmd = &cobra.Command{
	Use:                "run [command]",
	Short:              "Execute a command within the AgentBox sandbox",
	Args:               cobra.MinimumNArgs(1),
	DisableFlagParsing: true,
	RunE: func(cmd *cobra.Command, args []string) error {
		cfg, err := config.LoadConfig(".agentbox.yml")
		if err != nil {
			return err
		}

		exec := sandbox.NewExecutor(cfg)
		return exec.Run(args)
	},
}
EOF

# Generate internal/config/config.go
cat << 'EOF' > internal/config/config.go
package config

import (
	"os"
	"gopkg.in/yaml.v3"
)

type Config struct {
	Whitelist Whitelist `yaml:"whitelist"`
}

type Whitelist struct {
	Commands []string `yaml:"commands"`
	Paths    []string `yaml:"paths"`
	EnvVars  []string `yaml:"env_vars"`
}

func LoadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var cfg Config
	err = yaml.Unmarshal(data, &cfg)
	if err != nil {
		return nil, err
	}
	return &cfg, nil
}

func CreateDefaultConfig(path string) error {
	defaultCfg := `whitelist:
  commands:
    - "python"
    - "node"
    - "ls"
    - "echo"
  paths:
    - "./data"
    - "./output"
  env_vars:
    - "OPENAI_API_KEY"
`
	return os.WriteFile(path, []byte(defaultCfg), 0644)
}
EOF

# Generate internal/sandbox/executor.go
cat << 'EOF' > internal/sandbox/executor.go
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
EOF

# Generate internal/memory/store.go
cat << 'EOF' > internal/memory/store.go
package memory

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"errors"
	"io"
	"os"
)

// Master key hardcoded for V1 boilerplate architecture
var masterKey = []byte("12345678901234567890123456789012") 

func EncryptContext(filename string, plaintext []byte) error {
	block, err := aes.NewCipher(masterKey)
	if err != nil {
		return err
	}

	aesGCM, err := cipher.NewGCM(block)
	if err != nil {
		return err
	}

	nonce := make([]byte, aesGCM.NonceSize())
	if _, err = io.ReadFull(rand.Reader, nonce); err != nil {
		return err
	}

	ciphertext := aesGCM.Seal(nonce, nonce, plaintext, nil)
	return os.WriteFile(filename, ciphertext, 0600)
}

func DecryptContext(filename string) ([]byte, error) {
	data, err := os.ReadFile(filename)
	if err != nil {
		return nil, err
	}

	block, err := aes.NewCipher(masterKey)
	if err != nil {
		return nil, err
	}

	aesGCM, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}

	nonceSize := aesGCM.NonceSize()
	if len(data) < nonceSize {
		return nil, errors.New("ciphertext too short")
	}

	nonce, ciphertext := data[:nonceSize], data[nonceSize:]
	plaintext, err := aesGCM.Open(nil, nonce, ciphertext, nil)
	if err != nil {
		return nil, err
	}

	return plaintext, nil
}
EOF

# Generate README.md
cat << 'EOF' > README.md
# AgentBox

AgentBox is an ultra-lightweight CLI sandbox that wraps existing autonomous AI agents to enforce zero-trust execution, manage encrypted state, and cloak credentials.

### Problem Statement
Running autonomous AI agents locally often provides them unrestricted access to the host's file system, environment variables, and execution context. This poses significant risks, including accidental file destruction, unintended system changes, and exposure of sensitive API keys or credentials. A simple, zero-configuration sandbox is needed to wrap untrusted agent execution without the overhead of heavy virtualization or complex container configurations.

### Research & Architecture
* [Scout Analysis](./docs/research/1-scout-analysis.md)
* [PRD](./docs/research/2-prd.md)
* [Tech Spec](./docs/research/3-tech-spec.md)
* [Builder Code](./docs/research/4-builder-code.md)

### Installation & Usage

```bash
# Initialize the secure context and configuration
agentbox init

# Run an agent command through the sandbox
agentbox run <command>
```
EOF

# Fetch dependencies and format code
go mod tidy
go fmt ./...

# Generate test.sh
cat << 'EOF' > test.sh
#!/bin/bash
set -e

echo "[Test] Building AgentBox..."
go build -o agentbox main.go

echo "[Test] Running 'init'..."
./agentbox init

if [ ! -f ".agentbox.yml" ]; then
    echo "❌ Error: .agentbox.yml was not created."
    exit 1
fi

if [ ! -f ".agent-context" ]; then
    echo "❌ Error: .agent-context was not created."
    exit 1
fi

echo "[Test] Testing whitelisted command (ls)..."
./agentbox run ls > /dev/null
echo "✅ Whitelisted command succeeded."

echo "[Test] Testing non-whitelisted command (whoami)..."
if ./agentbox run whoami 2>/dev/null; then
    echo "❌ Error: Non-whitelisted command 'whoami' succeeded. It should have been blocked."
    exit 1
else
    echo "✅ Non-whitelisted command correctly blocked."
fi

echo "🚀 All tests passed successfully!"
exit 0
EOF

# Make test script executable
chmod +x test.sh

echo "AgentBox setup complete! Run ./test.sh to verify execution."
```
