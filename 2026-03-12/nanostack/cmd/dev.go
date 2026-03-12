package cmd

import (
	"fmt"
	"nanostack/internal/runner"

	"github.com/spf13/cobra"
)

var devCmd = &cobra.Command{
	Use:   "dev",
	Short: "Start the containerless native execution environment",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("⚡ Starting NanoStack Dev Server...")
		err := runner.StartNativeServer()
		if err != nil {
			fmt.Printf("❌ Dev server crashed: %v\n", err)
			return
		}
	},
}

func init() {
	rootCmd.AddCommand(devCmd)
}
