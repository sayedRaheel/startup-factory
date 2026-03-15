package main

import (
	"fmt"
	"os"
	"strings"

	"github.com/fatih/color"
	"github.com/spf13/cobra"

	"github.com/devscope/devscope/internal/project"
	"github.com/devscope/devscope/internal/shell"
	"github.com/devscope/devscope/internal/ui"
)

var rootCmd = &cobra.Command{
	Use:   "devscope",
	Short: "DevScope ensures consistent development environments.",
	Long: `DevScope ruthlessly eliminates local environment drift, ensuring every project's
development environment is precisely consistent and immediately ready.`,
	SilenceUsage:  true,
	SilenceErrors: true, // We handle errors explicitly
	Run: func(cmd *cobra.Command, args []string) {
		// Default behavior: Check environment if no command is specified.
		ui.Info("Running ambient environment check...")
		err := project.ValidateCurrentProjectEnvironment()
		if err != nil {
			ui.Error(fmt.Sprintf("Environment check failed: %v", err))
			ui.Warn("Run 'devscope fix' to resolve inconsistencies.")
			os.Exit(1)
		}
		ui.Success("Environment is consistent!")
	},
}

var fixCmd = &cobra.Command{
	Use:   "fix",
	Short: "Resolves local environment inconsistencies.",
	Long: `The 'fix' command intelligently resolves discrepancies between your current
environment and the project's devscope.yaml, installing missing tools and
setting environment variables without polluting global system paths.`,
	Run: func(cmd *cobra.Command, args []string) {
		ui.Info("Attempting to fix environment inconsistencies...")
		err := project.FixCurrentProjectEnvironment()
		if err != nil {
			ui.Error(fmt.Sprintf("Failed to fix environment: %v", err))
			os.Exit(1)
		}
		ui.Success("Environment fixed and consistent!")
	},
}

var shellHookCmd = &cobra.Command{
	Use:   "shell-hook [shell_type]",
	Short: "Outputs shell integration script for DevScope.",
	Long: `Outputs a shell script snippet to integrate DevScope with your shell (e.g., bash, zsh).
This script enables automatic environment validation upon 'cd' into a project.

Example for zsh:
  echo 'eval "$(devscope shell-hook zsh)"' >> ~/.zshrc

Example for bash:
  echo 'eval "$(devscope shell-hook bash)"' >> ~/.bashrc
`,
	Args: cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		shellType := strings.ToLower(args[0])
		script, err := shell.GenerateHookScript(shellType)
		if err != nil {
			ui.Error(fmt.Sprintf("Failed to generate shell hook for %s: %v", shellType, err))
			os.Exit(1)
		}
		fmt.Println(script)
	},
}

var shellEnvPathsCmd = &cobra.Command{
	Use:    "shell-env-paths",
	Hidden: true, // Internal command for shell hook
	Short:  "Internal: Outputs environment paths for the shell hook.",
	Run: func(cmd *cobra.Command, args []string) {
		paths, err := project.GetEnvironmentPaths()
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error getting env paths: %v\n", err)
			os.Exit(1)
		}
		for _, p := range paths {
			fmt.Println(p)
		}
	},
}

var shellEnvVarsCmd = &cobra.Command{
	Use:    "shell-env-vars",
	Hidden: true, // Internal command for shell hook
	Short:  "Internal: Outputs environment variables for the shell hook.",
	Run: func(cmd *cobra.Command, args []string) {
		envs, err := project.GetEnvironmentVariables()
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error getting env vars: %v\n", err)
			os.Exit(1)
		}
		for k, v := range envs {
			fmt.Printf("%s=%s\n", k, v)
		}
	},
}

func init() {
	rootCmd.AddCommand(fixCmd)
	rootCmd.AddCommand(shellHookCmd)
	rootCmd.AddCommand(shellEnvPathsCmd)
	rootCmd.AddCommand(shellEnvVarsCmd)
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		ui.Error(fmt.Sprintf("Error: %v", err))
		os.Exit(1)
	}
}
