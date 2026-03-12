package cmd

import (
	"fmt"
	"nanostack/internal/analyzer"

	"github.com/spf13/cobra"
)

var initCmd = &cobra.Command{
	Use:   "init",
	Short: "Analyze and condense existing workloads",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("🚀 Analyzing docker-compose.yml...")
		err := analyzer.ParseAndCondense("docker-compose.yml")
		if err != nil {
			fmt.Printf("❌ Failed to analyze: %v\n", err)
			return
		}
		fmt.Println("✅ Workload condensed! Heavy dependencies swapped for SQLite/DuckDB.")
	},
}

func init() {
	rootCmd.AddCommand(initCmd)
}
