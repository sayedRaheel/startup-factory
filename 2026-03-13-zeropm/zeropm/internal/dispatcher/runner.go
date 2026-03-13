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
		task, err := g.Vertex(taskID)
		if err != nil {
			return fmt.Errorf("failed to retrieve task %s from graph: %w", taskID, err)
		}

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
