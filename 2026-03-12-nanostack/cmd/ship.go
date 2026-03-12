package cmd

import (
	"fmt"
	"nanostack/internal/deployer"

	"github.com/spf13/cobra"
)

var shipCmd = &cobra.Command{
	Use:   "ship",
	Short: "Compile and deploy as a single-binary to the edge",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("📦 Compiling ecosystem into a single artifact...")
		err := deployer.PushToEdge()
		if err != nil {
			fmt.Printf("❌ Deployment failed: %v\n", err)
			return
		}
		fmt.Println("🌐 Deployed successfully! Live URL: https://edge.nanostack.run/your-app")
	},
}

func init() {
	rootCmd.AddCommand(shipCmd)
}
