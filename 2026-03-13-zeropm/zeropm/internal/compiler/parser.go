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
