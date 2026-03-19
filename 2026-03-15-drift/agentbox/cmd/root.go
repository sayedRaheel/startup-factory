package cmd

import (
	"fmt"
	"github.com/spf13/cobra"
	"os"
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
