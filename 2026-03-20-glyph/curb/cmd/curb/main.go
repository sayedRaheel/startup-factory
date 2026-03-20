package main

import (
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/spf13/cobra"
	"github.com/yourorg/curb/internal/proxy"
	"github.com/yourorg/curb/internal/tui"
)

func main() {
	var budget float64
	var protect string

	var rootCmd = &cobra.Command{
		Use:   "curb [agent command]",
		Short: "Keep your AI agents on a leash.",
		Args:  cobra.MinimumNArgs(1),
		Run: func(cmd *cobra.Command, args []string) {
			p := proxy.NewProxy(args)

			// Fire up the target process inside the PTY
			if err := p.Start(); err != nil {
				fmt.Printf("Failed to wrap agent: %v\n", err)
				os.Exit(1)
			}

			// Initialize the HUD
			m := tui.InitialModel(p, budget)

			// Run the Bubble Tea program, taking over the terminal
			prog := tea.NewProgram(m, tea.WithAltScreen())

			if _, err := prog.Run(); err != nil {
				fmt.Printf("UI Error: %v\n", err)
				os.Exit(1)
			}

			// Ensure variables are utilized
			_ = protect
		},
	}

	rootCmd.Flags().Float64Var(&budget, "budget", 5.00, "Maximum API budget before auto-pause")
	rootCmd.Flags().StringVar(&protect, "protect", "src/**/*.ts", "Glob patterns of protected files")

	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
