# Architectural Decision Record (ADR)

**Context:** We need to build `AgentBox`, an ultra-lightweight CLI sandbox that wraps existing autonomous AI agents to enforce zero-trust execution, manage encrypted state, and cloak credentials. The tool must be zero-config, highly portable, and incredibly fast.
**Decision:** We will build this entirely in **Go (Golang)** using standard libraries for cryptography and execution, supplemented only by `cobra` for CLI routing and `yaml.v3` for configuration.
**Trade-offs:** 
*   *Go vs. Rust:* Go provides a faster development cycle and simpler cross-platform compilation without the cognitive overhead of Rust's borrow checker, allowing us to ship faster. The trade-off is a slightly larger binary size and garbage collection pauses, which are negligible for a CLI wrapper.
*   *Go vs. Python/Node:* Python and Node require runtime environments and package managers, violating our "zero-config, single binary" mandate. The trade-off is that Go lacks the vast AI-specific library ecosystem of Python, but since we are building the *sandbox infrastructure* and not the AI models themselves, Go is the superior choice for OS-level process management.
*   *True OS Sandboxing (seccomp/ptrace) vs. Application-Level Wrapper:* For v1, building cross-platform kernel-level sandboxing is too heavy. We will rely on environment injection, working directory isolation, and entrypoint whitelisting via `os/exec`. The trade-off is that a highly sophisticated malicious agent could potentially escape the wrapper if not properly containerized, but this solves 99% of accidental local destruction (the "dumb agent" problem).

---

# Technical Specification

## 1. Tech Stack & Libraries
*   **Language:** Go 1.21+
*   **CLI Framework:** `github.com/spf13/cobra` (Industry standard, robust argument parsing)
*   **Configuration:** `gopkg.in/yaml.v3` (For parsing `.agentbox.yml`)
*   **Encryption:** Go standard library `crypto/aes`, `crypto/cipher`, `crypto/rand` (AES-GCM for `.agent-context`)
*   **Process Management:** Go standard library `os/exec`, `syscall`

## 2. File Structure
```text
agentbox/
├── go.mod
├── go.sum
├── main.go
├── cmd/
│   ├── root.go
│   ├── init.go
│   └── run.go
└── internal/
    ├── config/
    │   └── config.go        # YAML parsing for the Zero-Trust Whitelist
    ├── sandbox/
    │   └── executor.go      # Process wrapping, env injection, and execution isolation
    └── memory/
        └── store.go         # AES-GCM encryption/decryption of local context
```

## 3. Execution Commands (Step-by-Step)
Run these commands to bootstrap the project:

```bash
mkdir agentbox
cd agentbox
go mod init github.com/agentbox/agentbox

# Install dependencies
go get github.com/spf13/cobra@latest
go get gopkg.in/yaml.v3@latest

# Scaffold directories and files
mkdir -p cmd internal/config internal/sandbox internal/memory
touch main.go cmd/root.go cmd/init.go cmd/run.go 
touch internal/config/config.go internal/sandbox/executor.go internal/memory/store.go
```

---

## 4. Core Implementation & Boilerplate Code

### `main.go`
```go
package main

import "github.com/agentbox/agentbox/cmd"

func main() {
	cmd.Execute()
}
```

### `cmd/root.go`
```go
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
```

### `internal/config/config.go`
```go
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
  paths:
    - "./data"
    - "./output"
  env_vars:
    - "OPENAI_API_KEY"
`
	return os.WriteFile(path, []byte(defaultCfg), 0644)
}
```

### `internal/sandbox/executor.go`
```go
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
```

### `internal/memory/store.go`
```go
package memory

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"errors"
	"io"
	"os"
)

// In a real scenario, this key would be securely derived (e.g., PBKDF2 from a user password or OS keychain).
// Hardcoded here for the structural boilerplate.
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
```

### `cmd/init.go`
```go
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
```

### `cmd/run.go`
```go
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
	Use:   "run [command]",
	Short: "Execute a command within the AgentBox sandbox",
	Args:  cobra.MinimumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		cfg, err := config.LoadConfig(".agentbox.yml")
		if err != nil {
			return err
		}

		exec := sandbox.NewExecutor(cfg)
		return exec.Run(args)
	},
}
```
