package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "nanostack",
	Short: "NanoStack condenses heavy containerized workloads into embedded architectures.",
	Long:  `A local-first CLI that automatically parses bloated architecture files and swaps heavy daemon dependencies with highly optimized embedded equivalents.`,
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
