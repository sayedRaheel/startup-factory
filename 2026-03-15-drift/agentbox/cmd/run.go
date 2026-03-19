package cmd

import (
	"github.com/agentbox/agentbox/internal/config"
	"github.com/agentbox/agentbox/internal/sandbox"
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(runCmd)
}

var runCmd = &cobra.Command{
	Use:                "run [command]",
	Short:              "Execute a command within the AgentBox sandbox",
	Args:               cobra.MinimumNArgs(1),
	DisableFlagParsing: true,
	RunE: func(cmd *cobra.Command, args []string) error {
		cfg, err := config.LoadConfig(".agentbox.yml")
		if err != nil {
			return err
		}

		exec := sandbox.NewExecutor(cfg)
		return exec.Run(args)
	},
}
