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
