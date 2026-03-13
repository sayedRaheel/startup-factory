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
