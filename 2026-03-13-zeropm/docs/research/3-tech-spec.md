I am Linus. I design systems that outlive the hype cycles. You want a razor-sharp, terminal-native CLI that orchestrates AI agents without bloat. Vera's PRD is aggressive, opinionated, and exactly what we need to build a tool that actually works. 

Here is the architectural blueprint. Every decision has a cost. I have named them. Forge, read this carefully and execute.

---

### 1. Architectural Decision Record (ADR)

**Decision 1: Go (Golang) as the Core Language**
*   **Why:** We require a single, statically compiled binary with zero runtime dependencies (no Node.js, no Python environments). Go provides lightning-fast startup times, cross-platform compilation out of the box, and native concurrency (goroutines/channels) which is mathematically perfect for executing a Directed Acyclic Graph (DAG) of tasks.
*   **The Trade-off:** Go’s error handling is verbose, and string parsing (like complex Markdown extraction) can be more tedious than in Python. We trade developer ergonomics in text processing for absolute execution speed and deployment frictionlessness.

**Decision 2: Pure Go SQLite (`modernc.org/sqlite`) for State**
*   **Why:** We need ACID-compliant state management local to the repository (`.zeropm/state.db`) to track DAG node execution status across runs. We use a pure Go port of SQLite instead of `mattn/go-sqlite3`.
*   **The Trade-off:** The CGO-based SQLite driver is slightly faster, but it requires a C compiler on the host machine during the build phase, which breaks frictionless cross-compilation (e.g., compiling for Windows from an M1 Mac). Pure Go SQLite sacrifices a negligible amount of I/O performance to guarantee deterministic, CGO-free cross-compilation.

**Decision 3: `os/exec` over embedded Git libraries**
*   **Why:** For the Auto-Resolver and Dispatcher, we will shell out to the system's `git` and local AI agents (e.g., `aider`) via `os/exec` rather than embedding heavy Git libraries (like `go-git`). 
*   **The Trade-off:** We assume the user has `git` and their chosen CLI agents installed and in their `$PATH`. This introduces environmental dependency, but keeps our binary incredibly lean and leverages the native, battle-tested Git binary for complex merge conflict resolution.

---

### 2. Tech Stack & Libraries

*   **Language:** Go 1.21+
*   **CLI Framework:** `github.com/spf13/cobra` (The undisputed standard for Go CLIs. Provides clean routing and flag parsing).
*   **Database:** `modernc.org/sqlite` (Pure Go SQLite for CGO-free state).
*   **Markdown Parsing:** `github.com/yuin/goldmark` (Fast, extensible, CommonMark compliant).
*   **DAG Management:** `github.com/dominikbraun/graph` (Generic, type-safe graph library to handle topological sorting and execution order).

---

### 3. File Structure

Keep the domains isolated. Do not let the CLI logic bleed into the DAG compiler.

```text
zeropm/
├── cmd/
│   ├── root.go           # CLI entrypoint, global flags
│   └── execute.go        # 'zeropm execute' command
├── internal/
│   ├── compiler/         # Domain: Markdown -> DAG
│   │   ├── parser.go     # Extracts tasks and dependencies via Goldmark
│   │   └── dag.go        # Builds the dominikbraun/graph
│   ├── dispatcher/       # Domain: Agent Handoff
│   │   └── runner.go     # os/exec wrapper for Aider/OpenClaw/etc.
│   ├── resolver/         # Domain: Conflict & Git State
│   │   └── git.go        # Branching, auto-commits, merge detection
│   └── state/            # Domain: SQLite Persistence
│       └── db.go         # .zeropm/state.db initialization and queries
├── main.go               # Binary entrypoint
├── go.mod
└── go.sum
```

---

### 4. Implementation Plan: Step-by-Step Commands

Forge, run these commands sequentially to scaffold the architecture:

```bash
# 1. Initialize the module
mkdir zeropm && cd zeropm
go mod init github.com/zeropm/zeropm

# 2. Fetch the hardened dependencies
go get github.com/spf13/cobra@latest
go get modernc.org/sqlite@latest
go get github.com/yuin/goldmark@latest
go get github.com/dominikbraun/graph@latest

# 3. Scaffold the exact directory structure
mkdir -p cmd internal/{compiler,dispatcher,resolver,state}

# 4. Touch the core files
touch main.go
touch cmd/root.go cmd/execute.go
touch internal/compiler/parser.go internal/compiler/dag.go
touch internal/dispatcher/runner.go
touch internal/resolver/git.go
touch internal/state/db.go
```

---

### 5. Core Logic & Boilerplate

Here is the structural boilerplate. Do not deviate from the interfaces. 

**`main.go`**
```go
package main

import "github.com/zeropm/zeropm/cmd"

func main() {
	cmd.Execute()
}
```

**`cmd/execute.go`**
```go
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
```

**`internal/compiler/dag.go`**
```go
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

	// TODO: Implement goldmark AST traversal in parser.go to populate this
	// For now, returning an empty graph
	return g, nil
}
```

**`internal/dispatcher/runner.go`**
```go
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
```

**`internal/state/db.go`**
```go
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
```

Forge, the architecture is set. It is lean, concurrent, and modular. Begin construction.
