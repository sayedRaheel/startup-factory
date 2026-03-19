package cmd

import (
	"fmt"
	"github.com/agentbox/agentbox/internal/config"
	"github.com/agentbox/agentbox/internal/memory"
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(initCmd)
}

var initCmd = &cobra.Command{
	Use:   "init",
	Short: "Initialize AgentBox in the current directory",
	RunE: func(cmd *cobra.Command, args []string) error {
		err := config.CreateDefaultConfig(".agentbox.yml")
		if err != nil {
			return err
		}

		err = memory.EncryptContext(".agent-context", []byte("{}"))
		if err != nil {
			return err
		}

		fmt.Println("✅ Initialization complete. Created .agentbox.yml and secure .agent-context")
		return nil
	},
}
