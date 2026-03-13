```bash
#!/usr/bin/env bash

# Goal Alignment Trace:
# I am writing this bash script -> because the Architect (Linus) specified this exact Go stack -> because it solves the PRD's requirement for a zero-dependency, compiled DAG task orchestrator -> because we want to earn GitHub stars by delivering a system that outlives hype cycles.

set -euo pipefail

echo "=> Forging ZeroPM..."

# 1. Initialize the module
mkdir -p zeropm
cd zeropm

echo "=> Initializing Go module..."
go mod init github.com/zeropm/zeropm

# 2. Fetch the hardened dependencies
# Note: Resolved version tag templating to use Go standard '@latest'
echo "=> Fetching dependencies..."
go get github.com/spf13/cobra@latest
go get modernc.org/sqlite@latest
go get github.com/yuin/goldmark@latest
go get github.com/dominikbraun/graph@latest

# 3. Scaffold the exact directory structure
echo "=> Structuring directories..."
mkdir -p cmd internal/{compiler,dispatcher,resolver,state}

# 4. Generate core files
echo "=> Writing core source files..."

cat << 'EOF' > main.go
package main

import "github.com/zeropm/zeropm/cmd"

func main() {
	cmd.Execute()
}
EOF

cat << 'EOF' > cmd/root.go
package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "zeropm",
	Short: "ZeroPM orchestrates AI agents efficiently.",
	Long:  `A razor-sharp, terminal-native CLI that orchestrates AI agents without bloat using a local DAG.`,
}

// Execute adds all child commands to the root command and sets flags appropriately.
func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}
EOF

cat << 'EOF' > cmd/execute.go
package cmd

import (
	"fmt"
	"github.com/spf13/cobra"
	"github.com/zeropm/zeropm/internal/compiler"
	"github.com/zeropm/zeropm/internal/dispatcher"
	"github.com/zeropm/zeropm/internal/state"
)

var executeCmd = &cobra.Command{
	Use:   "execute [file.md]",
	Short: "Parses a PRD and autonomously dispatches tasks to local agents",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		prdPath := args[0]
		
		// 1. Init local state
		db, err := state.InitDB()
		if err != nil {
			return fmt.Errorf("state init failed: %w", err)
		}
		defer db.Close()

		// 2. Compile PRD to DAG
		taskGraph, err := compiler.ParseToDAG(prdPath)
		if err != nil {
			return fmt.Errorf("DAG compilation failed: %w", err)
		}

		// 3. Dispatch & Resolve
		err = dispatcher.RunGraph(taskGraph, db)
		if err != nil {
			return fmt.Errorf("execution halted: %w", err)
		}

		fmt.Println("ZeroPM Execution Complete. Review your Git tree.")
		return nil
	},
}

func init() {
	rootCmd.AddCommand(executeCmd)
}
EOF

cat << 'EOF' > internal/compiler/parser.go
package compiler

import (
	"os"
	"github.com/yuin/goldmark"
)

// ParseMarkdown reads the PRD and uses Goldmark to extract the AST.
// Implementation pending for robust DAG extraction.
func ParseMarkdown(filepath string) error {
	_, err := os.ReadFile(filepath)
	if err != nil {
		return err
	}
	
	// TODO: Implement Markdown AST parsing and task extraction logic
	_ = goldmark.New()
	return nil
}
EOF

cat << 'EOF' > internal/compiler/dag.go
package compiler

import (
	"github.com/dominikbraun/graph"
)

// Task represents a single node in the DAG
type Task struct {
	ID           string
	Description  string
	Dependencies []string // IDs of tasks that must complete first
}

// ParseToDAG orchestrates reading the Markdown and returning an executable graph
func ParseToDAG(filepath string) (graph.Graph[string, Task], error) {
	g := graph.New(func(t Task) string {
		return t.ID
	}, graph.Directed(), graph.PreventCycles())

	// TODO: Implement goldmark AST traversal in parser.go to populate this graph
	// For now, returning an empty graph structure
	return g, nil
}
EOF

cat << 'EOF' > internal/dispatcher/runner.go
package dispatcher

import (
	"fmt"
	"os"
	"os/exec"
	"github.com/dominikbraun/graph"
	"github.com/zeropm/zeropm/internal/compiler"
	"database/sql"
)

// RunGraph performs a topological sort and executes tasks concurrently where possible
func RunGraph(g graph.Graph[string, compiler.Task], db *sql.DB) error {
	order, err := graph.TopologicalSort(g)
	if err != nil {
		return fmt.Errorf("cycle detected in dependencies: %w", err)
	}

	for _, taskID := range order {
		task, _ := g.Vertex(taskID)
		fmt.Printf("Dispatching task: %s\n", task.ID)
		
		// Execute the agent via standard I/O
		// Assuming 'aider' as the default agent for this boilerplate
		cmd := exec.Command("aider", "--message", task.Description)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		cmd.Stdin = os.Stdin // Allow human intervention if Aider prompts

		if err := cmd.Run(); err != nil {
			return fmt.Errorf("agent execution failed on task %s: %w", task.ID, err)
		}

		// TODO: Call internal/resolver to auto-commit state here
		// TODO: Update state.db marking task as complete
	}
	return nil
}
EOF

cat << 'EOF' > internal/resolver/git.go
package resolver

import (
	"fmt"
	"os/exec"
)

// CommitTask auto-commits the state of a completed task to git
func CommitTask(taskID string) error {
	cmd := exec.Command("git", "commit", "-am", fmt.Sprintf("chore(zeropm): auto-resolve task %s", taskID))
	return cmd.Run()
}
EOF

cat << 'EOF' > internal/state/db.go
package state

import (
	"database/sql"
	"os"
	"path/filepath"
	_ "modernc.org/sqlite"
)

// InitDB ensures the .zeropm directory exists and opens the SQLite connection
func InitDB() (*sql.DB, error) {
	dir := ".zeropm"
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, err
	}

	dbPath := filepath.Join(dir, "state.db")
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, err
	}

	// Create tables if they don't exist
	schema := `
	CREATE TABLE IF NOT EXISTS tasks (
		id TEXT PRIMARY KEY,
		status TEXT NOT NULL,
		commit_hash TEXT
	);`
	if _, err := db.Exec(schema); err != nil {
		return nil, err
	}

	return db, nil
}
EOF

echo "=> Tidy up go modules..."
go mod tidy

echo "=> ZeroPM architecture forged successfully. Ready for compilation."
```
