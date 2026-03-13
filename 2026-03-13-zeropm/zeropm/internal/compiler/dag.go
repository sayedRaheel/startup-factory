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
