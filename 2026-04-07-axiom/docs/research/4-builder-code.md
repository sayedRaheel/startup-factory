```bash
#!/usr/bin/env bash
set -e

echo "Starting Warden Environment Construction..."

# 1. Project directories setup
mkdir -p warden/cli warden/sandbox warden/executor warden/ledger docs/research

# 2. Setup Go module
cd warden
go mod init warden

# 3. Generating Source Code
echo "Generating src files..."

cat << 'EOF' > main.go
package main

import (
	"fmt"
	"log"
	"os"
	"warden/cli"
	"warden/executor"
	"warden/ledger"
	"warden/sandbox"
)

func main() {
	log.SetFlags(log.LstdFlags)

	if len(os.Args) < 2 {
		fmt.Println("Usage: warden run --agent <cmd> --prompt <txt> --verify-cmd <cmd>")
		os.Exit(1)
	}

	if os.Args[1] == "run" {
		config := cli.ParseArgs(os.Args[2:])

		log.Println("Starting Warden auto-verification loop...")
		currentDir, err := os.Getwd()
		if err != nil {
			log.Fatalf("Failed to get current dir: %v", err)
		}

		ledgerMgr := ledger.NewManager(currentDir)
		state, err := ledgerMgr.Load()
		if err != nil {
			log.Fatalf("Failed to load ledger: %v", err)
		}

		sb, err := sandbox.Init(currentDir)
		if err != nil {
			log.Fatalf("Sandbox init failed: %v", err)
		}
		defer sb.Cleanup()

		maxIterations := 3
		currentPrompt := config.Prompt

		for i := 1; i <= maxIterations; i++ {
			log.Printf("--- Iteration %d ---", i)

			err := executor.RunAgent(sb.SandboxPath, config.Agent, currentPrompt)
			if err != nil {
				log.Printf("Agent failed to run: %v", err)
				break
			}

			errTrace, err := executor.Verify(sb.SandboxPath, config.VerifyCmd)
			if err == nil {
				state.Attempts = append(state.Attempts, ledger.Attempt{Iteration: i, Success: true})
				if err := ledgerMgr.Save(state); err != nil {
					log.Printf("Warning: Failed to save ledger: %v", err)
				}

				if err := sb.MergeToMain(); err != nil {
					log.Fatalf("Failed to merge: %v", err)
				}
				log.Println("Agent task verified and merged successfully.")
				break
			} else {
				state.Attempts = append(state.Attempts, ledger.Attempt{Iteration: i, ErrorTrace: errTrace, Success: false})
				if err := ledgerMgr.Save(state); err != nil {
					log.Printf("Warning: Failed to save ledger: %v", err)
				}

				log.Println("Tests failed. Formatting error trace for next agent iteration...")
				currentPrompt = fmt.Sprintf("Your previous attempt failed. Fix the code to pass the tests.\n\nOriginal prompt: %s\n\nTest Error Output:\n%s", config.Prompt, errTrace)
			}
		}
	} else {
		fmt.Printf("Unknown command: %s\n", os.Args[1])
		os.Exit(1)
	}
}
EOF

cat << 'EOF' > cli/cli.go
package cli

import (
	"flag"
	"fmt"
	"os"
)

type Config struct {
	Agent     string
	Prompt    string
	VerifyCmd string
}

func ParseArgs(args []string) Config {
	fs := flag.NewFlagSet("run", flag.ExitOnError)
	agent := fs.String("agent", "", "The agent command to execute")
	prompt := fs.String("prompt", "", "The task/prompt for the agent")
	verify := fs.String("verify-cmd", "", "The test command to verify")

	fs.Parse(args)

	if *agent == "" || *prompt == "" || *verify == "" {
		fmt.Println("Missing required arguments. Use --agent, --prompt, and --verify-cmd.")
		os.Exit(1)
	}

	return Config{
		Agent:     *agent,
		Prompt:    *prompt,
		VerifyCmd: *verify,
	}
}
EOF

cat << 'EOF' > sandbox/sandbox.go
package sandbox

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

type Sandbox struct {
	WorkspaceRoot string
	SandboxPath   string
	BranchName    string
}

func Init(workspaceRoot string) (*Sandbox, error) {
	cmd := exec.Command("git", "rev-parse", "--is-inside-work-tree")
	cmd.Dir = workspaceRoot
	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("Not a git repository. Warden requires a git repository to manage worktrees")
	}

	branchName := fmt.Sprintf("warden-sandbox-%d", time.Now().UnixNano())
	sandboxPath := filepath.Join(workspaceRoot, ".warden", "sandbox")

	os.RemoveAll(sandboxPath)

	log.Printf("Creating ephemeral git worktree at %s", sandboxPath)
	addCmd := exec.Command("git", "worktree", "add", "-b", branchName, sandboxPath)
	addCmd.Dir = workspaceRoot
	if out, err := addCmd.CombinedOutput(); err != nil {
		return nil, fmt.Errorf("git worktree add failed: %s", string(out))
	}

	return &Sandbox{
		WorkspaceRoot: workspaceRoot,
		SandboxPath:   sandboxPath,
		BranchName:    branchName,
	}, nil
}

func (s *Sandbox) MergeToMain() error {
	log.Printf("Tests passed. Merging %s into main workspace...", s.BranchName)

	addCmd := exec.Command("git", "add", ".")
	addCmd.Dir = s.SandboxPath
	if err := addCmd.Run(); err != nil {
		return err
	}

	statusCmd := exec.Command("git", "status", "--porcelain")
	statusCmd.Dir = s.SandboxPath
	out, _ := statusCmd.Output()

	if strings.TrimSpace(string(out)) != "" {
		commitCmd := exec.Command("git", "commit", "-m", "Warden automated commit")
		commitCmd.Dir = s.SandboxPath
		if err := commitCmd.Run(); err != nil {
			return err
		}
	}

	// Use fast-forward merge since we branched directly from main
	mergeCmd := exec.Command("git", "merge", "--ff-only", s.BranchName)
	mergeCmd.Dir = s.WorkspaceRoot
	if out, err := mergeCmd.CombinedOutput(); err != nil {
		return fmt.Errorf("merge failed: %s", string(out))
	}

	return nil
}

func (s *Sandbox) Cleanup() {
	log.Println("Destroying ephemeral sandbox...")

	rmCmd := exec.Command("git", "worktree", "remove", "-f", s.SandboxPath)
	rmCmd.Dir = s.WorkspaceRoot
	rmCmd.Run()

	brCmd := exec.Command("git", "branch", "-D", s.BranchName)
	brCmd.Dir = s.WorkspaceRoot
	brCmd.Run()

	os.RemoveAll(s.SandboxPath)
}
EOF

cat << 'EOF' > executor/executor.go
package executor

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"
)

func splitCommand(cmd string) []string {
	return strings.Fields(cmd)
}

func RunAgent(sandboxPath, agentCmd, prompt string) error {
	log.Printf("Spawning agent: %s", agentCmd)

	parts := splitCommand(agentCmd)
	if len(parts) == 0 {
		return fmt.Errorf("empty agent command")
	}

	prog := parts[0]
	args := append(parts[1:], prompt)

	cmd := exec.Command(prog, args...)
	cmd.Dir = sandboxPath
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("agent execution failed: %v", err)
	}
	return nil
}

func Verify(sandboxPath, verifyCmd string) (string, error) {
	log.Printf("Running verification suite: %s", verifyCmd)

	parts := splitCommand(verifyCmd)
	if len(parts) == 0 {
		return "", fmt.Errorf("empty verify command")
	}

	cmd := exec.Command(parts[0], parts[1:]...)
	cmd.Dir = sandboxPath

	out, err := cmd.CombinedOutput()
	if err != nil {
		outputStr := strings.TrimSpace(string(out))
		log.Printf("Verification failed:\n%s", outputStr)
		return outputStr, err
	}

	return "", nil
}
EOF

cat << 'EOF' > ledger/ledger.go
package ledger

import (
	"encoding/json"
	"os"
	"path/filepath"
)

type Attempt struct {
	Iteration  int    `json:"iteration"`
	ErrorTrace string `json:"error_trace,omitempty"`
	Success    bool   `json:"success"`
}

type Ledger struct {
	Task     string    `json:"task"`
	Attempts []Attempt `json:"attempts"`
}

type Manager struct {
	Filepath string
}

func NewManager(workspaceRoot string) *Manager {
	wardenDir := filepath.Join(workspaceRoot, ".warden")
	if err := os.MkdirAll(wardenDir, 0755); err != nil {
		panic(err)
	}
	return &Manager{
		Filepath: filepath.Join(wardenDir, "ledger.json"),
	}
}

func (m *Manager) Load() (*Ledger, error) {
	if _, err := os.Stat(m.Filepath); os.IsNotExist(err) {
		return &Ledger{Attempts: []Attempt{}}, nil
	}
	data, err := os.ReadFile(m.Filepath)
	if err != nil {
		return nil, err
	}
	var l Ledger
	if err := json.Unmarshal(data, &l); err != nil {
		return nil, err
	}
	return &l, nil
}

func (m *Manager) Save(l *Ledger) error {
	data, err := json.MarshalIndent(l, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(m.Filepath, data, 0644)
}
EOF

echo "Building Warden Go binary..."
go build -o warden .
cd ..

# 4. Generate README.md
cat << 'EOF' > README.md
# Warden

Ephemeral execution firewall for local agents. Warden isolates agent workflows using Git worktrees, verifies them through a user-provided command, and safely merges only successful attempts.

### Problem Statement
Running autonomous LLM agents against local codebases is dangerous. They frequently overwrite working logic with hallucinated dependencies, make unverified breaking changes, and corrupt state. We need a zero-dependency, globally installable firewall that confines agents to verified sandboxes and merges changes strictly upon test success.

### Research & Architecture
* [Scout Analysis](./docs/research/1-scout-analysis.md)
* [PRD](./docs/research/2-prd.md)
* [Tech Spec](./docs/research/3-tech-spec.md)
* [Builder Code](./docs/research/4-builder-code.md)
EOF

# 5. Generate Test Execution Script
cat << 'EOF' > test.sh
#!/usr/bin/env bash
set -e

echo "Setting up Warden test environment sandbox..."
mkdir -p test_env
cd test_env

# Initialize dummy workspace
git init
git config user.email "test@warden.local"
git config user.name "Warden Test"

cat << 'INNER_EOF' > target.txt
buggy content
INNER_EOF

cat << 'INNER_EOF' > test_target.sh
#!/usr/bin/env bash
if grep -q "fixed content" target.txt; then
    echo "Test passed!"
    exit 0
else
    echo "Test failed: content is still buggy"
    exit 1
fi
INNER_EOF
chmod +x test_target.sh

cat << 'INNER_EOF' > dummy_agent.sh
#!/usr/bin/env bash
PROMPT="${@: -1}"
echo "Agent Received Prompt: $PROMPT"
if [[ "$PROMPT" == *"Your previous attempt failed"* ]]; then
    echo "Agent iteration 2: Fixing the file..."
    echo "fixed content" > target.txt
else
    echo "Agent iteration 1: Simulating hallucination/bug..."
    echo "still buggy content" > target.txt
fi
INNER_EOF
chmod +x dummy_agent.sh

git add target.txt test_target.sh dummy_agent.sh
git commit -m "Initial commit"

echo "Executing Warden firewall over dummy agent..."
../warden/warden run \
    --agent "./dummy_agent.sh" \
    --prompt "Fix the target.txt file" \
    --verify-cmd "./test_target.sh"

echo "Validating git merge integrity..."
if grep -q "fixed content" target.txt; then
    echo "SUCCESS: Agent bug was fixed and securely merged into main."
else
    echo "FAILURE: Fix was not merged."
    exit 1
fi

echo "Validating ledger state..."
if grep -q '"success": true' .warden/ledger.json; then
    echo "SUCCESS: Ledger correctly recorded the successful loop."
else
    echo "FAILURE: Ledger state invalid."
    exit 1
fi

echo "All tests completed with Exit Code 0."
EOF
chmod +x test.sh

echo "Build complete. Running self-tests..."
./test.sh
```
