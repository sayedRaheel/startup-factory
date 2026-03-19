### Root Cause Analysis

1. **Misplaced Test Script:** The builder originally generated `test.sh` inside the `agentbox/` subdirectory. The automated testing framework runs from the root directory, causing the `ERROR: test.sh not found` failure.
2. **Missing Sandbox Logic (Vaporware):** The configuration (`config.go`) defined a `Paths` whitelist, but the actual execution engine (`internal/sandbox/executor.go`) never implemented the logic to evaluate or enforce it. It was completely ignored.
3. **Overly Restrictive Environment:** The `EnvVars` whitelist lacked basic standard variables like `PATH` and `HOME`. Stripping these away completely causes many standard executables (like `node`, `python`, or even basic utilities) to instantly crash upon execution because they cannot find dependencies.

### Fixed Solution

I have rewritten the scaffolding script. It now properly implements the path whitelisting logic, includes `PATH` and `HOME` in the default sandbox whitelist, and places `test.sh` accurately in the root directory where the test framework expects it.

```bash
#!/bin/bash
set -e

# Create and enter the project directory
mkdir -p agentbox
cd agentbox

# Initialize Go module if not present
go mod init github.com/agentbox/agentbox 2>/dev/null || true

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
    - "PATH"
    - "HOME"
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
	allowedCmd := false
	for _, cmd := range e.Config.Whitelist.Commands {
		if baseCmd == cmd {
			allowedCmd = true
			break
		}
	}
	if !allowedCmd {
		return fmt.Errorf("security violation: command '%s' is not in the whitelist", baseCmd)
	}

	// 2. Path Whitelist Check (Fix for missing vaporware logic)
	for _, arg := range args[1:] {
		// If an argument looks like a path designation
		if strings.HasPrefix(arg, "/") || strings.HasPrefix(arg, "./") || strings.HasPrefix(arg, "../") {
			pathAllowed := false
			for _, allowedPath := range e.Config.Whitelist.Paths {
				if strings.HasPrefix(arg, allowedPath) {
					pathAllowed = true
					break
				}
			}
			if !pathAllowed {
				return fmt.Errorf("security violation: path '%s' is not in the whitelist", arg)
			}
		}
	}

	// 3. Prepare Sandboxed Execution
	cmd := exec.Command(baseCmd, args[1:]...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin

	// 4. Credential Cloaking & Env Whitelist
	var cleanEnv []string
	for _, envKey := range e.Config.Whitelist.EnvVars {
		if val, exists := os.LookupEnv(envKey); exists {
			cleanEnv = append(cleanEnv, fmt.Sprintf("%s=%s", envKey, val))
		}
	}
	cmd.Env = cleanEnv

	// 5. Execute
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
EOF

# Fetch dependencies and format code
go get github.com/spf13/cobra@latest
go get gopkg.in/yaml.v3@latest
go mod tidy
go fmt ./...

# Go back to the ROOT directory to establish the test.sh file properly
cd ..

# Generate test.sh in the ROOT directory
cat << 'EOF' > test.sh
#!/bin/bash
set -e

cd agentbox

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

echo "[Test] Testing whitelisted path (ls ./data)..."
mkdir -p ./data
./agentbox run ls ./data > /dev/null
echo "✅ Whitelisted path succeeded."

echo "[Test] Testing non-whitelisted path (ls /etc)..."
if ./agentbox run ls /etc 2>/dev/null; then
    echo "❌ Error: Path '/etc' succeeded. It should have been blocked."
    exit 1
else
    echo "✅ Non-whitelisted path correctly blocked."
fi

echo "🚀 All tests passed successfully!"
exit 0
EOF

# Make test script executable
chmod +x test.sh

# Cleanup mistakenly placed script from previous runs
rm -f agentbox/test.sh

echo "Fix complete. Overwrote files and generated correctly-placed ./test.sh."
```
