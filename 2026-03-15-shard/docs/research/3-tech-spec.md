Architectural Decision Record (ADR): DevScope Initial Architecture

**Decision:** Utilize Go as the primary development language and operate without a dedicated database for DevScope.

**Justification for Go:**
The Product Requirements Document (PRD) explicitly recommends Go, a choice I concur with wholeheartedly. Go's strengths are perfectly aligned with DevScope's core goals:
1.  **Performance & Speed:** Go compiles to native machine code, providing excellent runtime performance and rapid startup times crucial for a CLI tool that needs to execute quickly and repeatedly (e.g., on `cd` events).
2.  **Cross-Platform Compilation:** Go's robust tooling allows for easy cross-compilation into static binaries for Windows, macOS, and Linux from a single codebase. This is vital for a tool targeting diverse developer environments and simplifying distribution (e.g., via `curl | bash` or `brew`).
3.  **Static Binaries & Minimal Dependencies:** Go applications can be deployed as single, self-contained binaries with no external runtime dependencies (unlike Python or Node.js applications). This drastically simplifies installation and eliminates "dependency hell" for the end-user, adhering to the "lean, fast, and easily distributable" mandate.
4.  **Concurrency Model:** While less critical for an initial CLI, Go's goroutines and channels provide a powerful and efficient model for handling concurrent operations, which could be beneficial for future features like parallel tool installations or background environment checks without blocking the main process.
5.  **Robust Standard Library:** Go's comprehensive standard library reduces reliance on third-party packages for common tasks like HTTP requests, file system operations, and archive handling, ensuring a stable and secure foundation.

**Trade-offs of Go:**
1.  **Binary Size:** Go binaries are typically larger than those compiled from C/C++ due to statically linking the runtime. For a CLI tool, this is generally negligible (MBs, not GBs) and far outweighed by the benefits of static compilation.
2.  **Learning Curve:** Developers accustomed to dynamic languages (Python, JavaScript) may find Go's strict type system and explicit error handling a slight adjustment. However, its simplicity and clear idioms make it relatively quick to become productive.

**Justification for No Database:**
DevScope's initial feature set primarily revolves around reading a local YAML file (`devscope.yaml`), inspecting the local system environment, and orchestrating local tool installations. There is no requirement for:
*   Persistent state that needs to survive across reboots or be shared across multiple machines.
*   Complex data relationships or querying.
*   Transactional integrity beyond basic file operations.
Storing tool metadata, download paths, or other operational details can be efficiently handled with simple file system caches or derived on demand. Introducing a database, even an embedded one like SQLite, would add unnecessary complexity, increase binary size, and introduce new failure modes for a tool whose ethos is "ruthlessly cut bloat."

**Trade-offs of No Database:**
1.  **Limited Complex State Management:** If future features require tracking historical data, complex user preferences, or project-specific configurations beyond what `devscope.yaml` can declaratively define, a database would become necessary. This decision is consciously made for V1 simplicity and can be revisited.
2.  **No Centralized Storage:** No inherent capability for centralized reporting or synchronization of environment states across a team, though this could be achieved via `devscope.yaml` version control.

---

### Technical Specification and Implementation Plan: DevScope

**1. Exact Tech Stack and Libraries:**

*   **Language:** Go (Golang)
*   **CLI Framework:** `github.com/spf13/cobra` (for robust command-line interface structure)
*   **YAML Parsing:** `gopkg.in/yaml.v3` (for `devscope.yaml` configuration)
*   **Configuration Management (for DevScope's internal config):** `github.com/spf13/viper` (optional, for DevScope's own settings, e.g., installation paths; can fallback to ENV/flags)
*   **Colored Output:** `github.com/fatih/color` (for user-friendly, actionable feedback)
*   **File System Operations:** Go's standard `os`, `io`, `path/filepath` packages.
*   **HTTP Downloads:** Go's standard `net/http` package.
*   **Archive Extraction:** Go's standard `archive/zip`, `archive/tar`, `compress/gzip` packages.
*   **Environment Variables:** Go's standard `os` package.
*   **Shell Execution:** Go's standard `os/exec` package.
*   **Platform Detection:** Go's standard `runtime` package.

**2. Exact File Structure:**

```
devscope/
├── main.go                     # Entry point, Cobra CLI definition (root, fix, shell-hook commands)
├── go.mod                      # Go module definition
├── go.sum                      # Go module checksums
├── .gitignore                  # Standard Go .gitignore
├── internal/                   # Internal packages, not intended for external consumption
│   ├── config/                 # Configuration parsing and structs
│   │   └── devscope_config.go  # Defines `DevScopeConfig` struct and YAML parsing logic
│   ├── project/                # Project environment detection and validation
│   │   └── project_env.go      # Locates `devscope.yaml`, validates current environment state
│   ├── shell/                  # Shell integration logic
│   │   └── shell_hook.go       # Generates shell snippets for `cd` hook (bash/zsh)
│   ├── tools/                  # Tool management and installation logic
│   │   ├── tool_manager.go     # Interface for tool installers, common download/extraction logic
│   │   ├── nodejs.go           # Node.js specific installation and version detection
│   │   ├── python.go           # Python specific installation and version detection
│   │   ├── golang.go           # Go specific installation and version detection
│   │   └── clitool.go          # Generic CLI tool installation (e.g., kubectl, helm)
│   ├── ui/                     # User interface components (output, prompts)
│   │   └── output.go           # Functions for colored console output
│   └── util/                   # General utility functions
│       └── filesystem.go       # File system operations (e.g., creating dirs, symlinks, finding project root)
│       └── downloader.go       # Generic file downloading utility with progress feedback
```

**3. Step-by-Step Commands to Run:**

```bash
# 1. Initialize the Go module
go mod init github.com/devscope/devscope # Or your desired module path

# 2. Install necessary Go dependencies
go get github.com/spf13/cobra@latest
go get github.com/spf13/viper@latest    # Only if Viper is used for DevScope's own config
go get gopkg.in/yaml.v3@latest
go get github.com/fatih/color@latest

# 3. Create the directory structure
mkdir -p internal/config
mkdir -p internal/project
mkdir -p internal/shell
mkdir -p internal/tools
mkdir -p internal/ui
mkdir -p internal/util

# 4. Create core files (touch empty files)
touch main.go
touch .gitignore
touch internal/config/devscope_config.go
touch internal/project/project_env.go
touch internal/shell/shell_hook.go
touch internal/tools/tool_manager.go
touch internal/tools/nodejs.go
touch internal/tools/python.go
touch internal/tools/golang.go
touch internal/tools/clitool.go
touch internal/ui/output.go
touch internal/util/filesystem.go
touch internal/util/downloader.go

# 5. Add .gitignore content
echo "
# Binaries for programs
*.exe
*.darwin-amd64
*.darwin-arm64
*.linux-amd64
*.linux-arm64
*.windows-amd64
*.windows-arm64

# Test binaries
*_test

# Editor/IDE files
.idea/
.vscode/
.DS_Store

# Go module cache
.cache/
" > .gitignore

# 6. Add initial devscope.yaml example for testing
echo "
# Example devscope.yaml
tools:
  node:
    version: "18.17.0"
  go:
    version: "1.21.0"
  python:
    version: "3.10.0"
  cli:
    kubectl:
      version: "1.27.0"
      url: "https://dl.k8s.io/release/v{version}/bin/linux/amd64/kubectl" # Example URL, replace {version}
    helm:
      version: "3.12.0"
      url: "https://get.helm.sh/helm-v{version}-linux-amd64.tar.gz" # Example URL

env:
  PROJECT_NAME: "DevScope"
  DATABASE_URL: "postgres://user:pass@host:5432/db"
  AWS_REGION: "us-east-1"
" > devscope.yaml
```

**4. Exact Logic and Boilerplate Code for Core Files:**

**`main.go`**

```go
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

func init() {
	rootCmd.AddCommand(fixCmd)
	rootCmd.AddCommand(shellHookCmd)
	// Optionally, add a 'sync' alias for 'fix'
	// rootCmd.AddCommand(&cobra.Command{
	// 	Use:   "sync",
	// 	Short: "Alias for 'fix' command.",
	// 	Run:   fixCmd.Run,
	// })
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		// Errors are handled by individual commands and ui.Error
		// This block catches any unhandled Cobra errors or panics
		ui.Error(fmt.Sprintf("Error: %v", err))
		os.Exit(1)
	}
}
```

**`internal/config/devscope_config.go`**

```go
package config

import (
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

const DevScopeConfigFileName = "devscope.yaml"

// DevScopeConfig represents the structure of the devscope.yaml file
type DevScopeConfig struct {
	Tools map[string]ToolConfig `yaml:"tools"`
	Env   map[string]string     `yaml:"env"`
}

// ToolConfig defines a generic tool configuration.
// It uses omitempty for optional fields and allows for specific CLI tool definitions.
type ToolConfig struct {
	Version string            `yaml:"version,omitempty"`
	URL     string            `yaml:"url,omitempty"`     // For CLI tools with custom download URLs
	Binary  string            `yaml:"binary,omitempty"`  // For CLI tools, expected binary name post-extraction
	Args    []string          `yaml:"args,omitempty"`    // Additional args for installation scripts (future)
	Tools   map[string]string `yaml:",inline"`           // For tools like 'cli' which have sub-configs
}

// ParseConfig reads and parses the devscope.yaml file from the given path.
func ParseConfig(configPath string) (*DevScopeConfig, error) {
	data, err := os.ReadFile(configPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read %s: %w", DevScopeConfigFileName, err)
	}

	var cfg DevScopeConfig
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("failed to parse %s: %w", DevScopeConfigFileName, err)
	}

	// Normalize ToolConfig for CLI tools defined inline
	if cfg.Tools == nil {
		cfg.Tools = make(map[string]ToolConfig)
	}
	if cliTools, ok := cfg.Tools["cli"]; ok {
		for name, version := range cliTools.Tools { // iterate over inline map
			if _, exists := cfg.Tools[name]; exists {
				return nil, fmt.Errorf("duplicate tool definition: '%s' found both as top-level and under 'cli'", name)
			}
			cfg.Tools[name] = ToolConfig{
				Version: version,
				URL:     cliTools.URL,     // These would need to be defined per CLI tool
				Binary:  cliTools.Binary,  // These would need to be defined per CLI tool
			}
		}
		delete(cfg.Tools, "cli") // Remove the generic 'cli' entry after processing
	}


	return &cfg, nil
}

// GetProjectConfigPath attempts to find devscope.yaml in the current directory or parent directories.
func GetProjectConfigPath() (string, error) {
	currentDir, err := os.Getwd()
	if err != nil {
		return "", fmt.Errorf("failed to get current working directory: %w", err)
	}

	for {
		configPath := filepath.Join(currentDir, DevScopeConfigFileName)
		if _, err := os.Stat(configPath); err == nil {
			return configPath, nil
		}
		parentDir := filepath.Dir(currentDir)
		if parentDir == currentDir { // Reached root directory
			break
		}
		currentDir = parentDir
	}

	return "", fmt.Errorf("%s not found in current directory or any parent directories", DevScopeConfigFileName)
}
```

**`internal/project/project_env.go`**

```go
package project

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/devscope/devscope/internal/config"
	"github.com/devscope/devscope/internal/tools"
	"github.com/devscope/devscope/internal/ui"
	"github.com/devscope/devscope/internal/util"
)

const (
	DevScopeProjectDir = ".devscope"
	BinDir             = "bin"
	ToolsDir           = "tools"
)

// GetProjectRoot returns the absolute path to the project root containing devscope.yaml
func GetProjectRoot() (string, error) {
	configPath, err := config.GetProjectConfigPath()
	if err != nil {
		return "", err
	}
	return filepath.Dir(configPath), nil
}

// GetDevScopeDirPath returns the absolute path to the .devscope directory within the project
func GetDevScopeDirPath() (string, error) {
	projectRoot, err := GetProjectRoot()
	if err != nil {
		return "", err
	}
	return filepath.Join(projectRoot, DevScopeProjectDir), nil
}

// GetDevScopeBinDirPath returns the absolute path to the .devscope/bin directory
func GetDevScopeBinDirPath() (string, error) {
	devscopeDir, err := GetDevScopeDirPath()
	if err != nil {
		return "", err
	}
	return filepath.Join(devscopeDir, BinDir), nil
}

// GetDevScopeToolsDirPath returns the absolute path to the .devscope/tools directory
func GetDevScopeToolsDirPath() (string, error) {
	devscopeDir, err := GetDevScopeDirPath()
	if err != nil {
		return "", err
	}
	return filepath.Join(devscopeDir, ToolsDir), nil
}

// ValidateCurrentProjectEnvironment checks if the current environment matches devscope.yaml.
// It returns an error if any discrepancies are found.
func ValidateCurrentProjectEnvironment() error {
	configPath, err := config.GetProjectConfigPath()
	if err != nil {
		return fmt.Errorf("project config not found: %w", err)
	}

	cfg, err := config.ParseConfig(configPath)
	if err != nil {
		return fmt.Errorf("failed to parse devscope.yaml: %w", err)
	}

	ui.Info(fmt.Sprintf("Validating environment for project: %s", filepath.Dir(configPath)))

	// --- Validate Tools ---
	var toolErrors []error
	toolManager := tools.NewToolManager()
	for toolName, toolCfg := range cfg.Tools {
		// Determine the actual tool type
		var installer tools.ToolInstaller
		switch strings.ToLower(toolName) {
		case "node":
			installer = tools.NewNodeJSInstaller()
		case "go":
			installer = tools.NewGolangInstaller()
		case "python":
			installer = tools.NewPythonInstaller()
		default:
			// Assume it's a generic CLI tool if not a known language runtime
			installer = tools.NewCLIToolInstaller(toolName, toolCfg.URL, toolCfg.Binary)
		}

		if err := toolManager.CheckToolVersion(installer, toolCfg.Version); err != nil {
			toolErrors = append(toolErrors, fmt.Errorf("%s %s required: %w", toolName, toolCfg.Version, err))
		}
	}
	if len(toolErrors) > 0 {
		return fmt.Errorf("tool discrepancies found:\n- %s", strings.Join(util.ErrorsToStrings(toolErrors), "\n- "))
	}

	// --- Validate Environment Variables ---
	var envErrors []error
	for key, expectedValue := range cfg.Env {
		currentValue := os.Getenv(key)
		if currentValue == "" {
			envErrors = append(envErrors, fmt.Errorf("environment variable '%s' is not set", key))
		} else if currentValue != expectedValue {
			envErrors = append(envErrors, fmt.Errorf("environment variable '%s' mismatch: expected '%s', got '%s'", key, expectedValue, currentValue))
		}
	}
	if len(envErrors) > 0 {
		return fmt.Errorf("environment variable discrepancies found:\n- %s", strings.Join(util.ErrorsToStrings(envErrors), "\n- "))
	}

	return nil // No discrepancies found
}

// FixCurrentProjectEnvironment attempts to resolve discrepancies.
func FixCurrentProjectEnvironment() error {
	projectRoot, err := GetProjectRoot()
	if err != nil {
		return fmt.Errorf("project config not found: %w", err)
	}
	devscopeDir, err := GetDevScopeDirPath()
	if err != nil {
		return fmt.Errorf("could not determine .devscope directory: %w", err)
	}
	binDir, err := GetDevScopeBinDirPath()
	if err != nil {
		return fmt.Errorf("could not determine .devscope/bin directory: %w", err)
	}
	toolsDir, err := GetDevScopeToolsDirPath()
	if err != nil {
		return fmt.Errorf("could not determine .devscope/tools directory: %w", err)
	}

	// Ensure .devscope, .devscope/bin, and .devscope/tools directories exist
	if err := os.MkdirAll(binDir, 0755); err != nil {
		return fmt.Errorf("failed to create %s: %w", binDir, err)
	}
	if err := os.MkdirAll(toolsDir, 0755); err != nil {
		return fmt.Errorf("failed to create %s: %w", toolsDir, err)
	}

	configPath := filepath.Join(projectRoot, config.DevScopeConfigFileName)
	cfg, err := config.ParseConfig(configPath)
	if err != nil {
		return fmt.Errorf("failed to parse devscope.yaml: %w", err)
	}

	ui.Info(fmt.Sprintf("Fixing environment for project: %s", projectRoot))

	// --- Install/Update Tools ---
	toolManager := tools.NewToolManager()
	for toolName, toolCfg := range cfg.Tools {
		ui.Info(fmt.Sprintf("Checking/Installing %s %s...", toolName, toolCfg.Version))
		var installer tools.ToolInstaller
		switch strings.ToLower(toolName) {
		case "node":
			installer = tools.NewNodeJSInstaller()
		case "go":
			installer = tools.NewGolangInstaller()
		case "python":
			installer = tools.NewPythonInstaller()
		default:
			installer = tools.NewCLIToolInstaller(toolName, toolCfg.URL, toolCfg.Binary)
		}

		installDir := filepath.Join(toolsDir, toolName, toolCfg.Version) // e.g., .devscope/tools/node/18.17.0
		if err := installer.Install(toolCfg.Version, installDir, binDir); err != nil {
			return fmt.Errorf("failed to install %s %s: %w", toolName, toolCfg.Version, err)
		}
		ui.Success(fmt.Sprintf("%s %s is ready.", toolName, toolCfg.Version))
	}

	// --- Handle Environment Variables ---
	// For 'fix', we don't *set* environment variables globally.
	// We rely on the shell hook to set them for the current session.
	// Here, we just ensure the user is aware of what *will* be set.
	ui.Info("Environment variables will be set by the DevScope shell hook:")
	for key, value := range cfg.Env {
		ui.Success(fmt.Sprintf("  %s=%s", key, value))
	}

	return nil
}

// GetEnvironmentPaths returns the PATH entries that should be added for this project.
// This is used by the shell hook.
func GetEnvironmentPaths() ([]string, error) {
	configPath, err := config.GetProjectConfigPath()
	if err != nil {
		return nil, nil // No config, no special paths
	}

	cfg, err := config.ParseConfig(configPath)
	if err != nil {
		return nil, fmt.Errorf("failed to parse devscope.yaml for paths: %w", err)
	}

	projectRoot, err := GetProjectRoot()
	if err != nil {
		return nil, err
	}
	devscopeBin := filepath.Join(projectRoot, DevScopeProjectDir, BinDir)
	devscopeTools := filepath.Join(projectRoot, DevScopeProjectDir, ToolsDir)

	var paths []string
	paths = append(paths, devscopeBin) // Add .devscope/bin first

	for toolName, toolCfg := range cfg.Tools {
		// Construct the specific bin path for each installed tool
		// e.g., .devscope/tools/node/18.17.0/bin
		toolBinPath := filepath.Join(devscopeTools, toolName, toolCfg.Version, BinDir)
		if _, err := os.Stat(toolBinPath); err == nil { // Only add if directory exists
			paths = append(paths, toolBinPath)
		}
	}
	return paths, nil
}

// GetEnvironmentVariables returns the environment variables that should be set for this project.
// This is used by the shell hook.
func GetEnvironmentVariables() (map[string]string, error) {
	configPath, err := config.GetProjectConfigPath()
	if err != nil {
		return nil, nil // No config, no special env vars
	}

	cfg, err := config.ParseConfig(configPath)
	if err != nil {
		return nil, fmt.Errorf("failed to parse devscope.yaml for env vars: %w", err)
	}
	return cfg.Env, nil
}

```

**`internal/shell/shell_hook.go`**

```go
package shell

import (
	"fmt"
	"os"
	"strings"

	"github.com/devscope/devscope/internal/project"
)

const (
	hookScriptTemplate = `
_devscope_chpwd_hook() {
  local project_root="%s" # This will be replaced by the actual project root if found
  local devscope_bin="%s" # This will be replaced by the actual .devscope/bin
  local devscope_tools_bin="%s" # This will be replaced by path to tool binaries

  # Check if in a project directory with devscope.yaml
  config_path=$(devscope_find_config)
  if [[ -n "$config_path" ]]; then
    # Reset PATH and ENV to system defaults first
    PATH="%s"
    # Iterate through and unset project-specific env vars
    for env_var_name in $(compgen -v | grep '^DEVSCOPE_ENV_'); do
      unset "${env_var_name#DEVSCOPE_ENV_}"
    done

    # Get project-specific paths and env vars from DevScope CLI
    # We call devscope inside the hook to ensure it's always up-to-date
    # on tool installation paths.
    local new_paths=$(devscope shell-env-paths 2>/dev/null)
    local project_env_vars_output=$(devscope shell-env-vars 2>/dev/null)

    # Add DevScope-managed paths to PATH
    if [[ -n "$new_paths" ]]; then
      IFS=$'\n' read -r -d '' -a path_array <<< "$new_paths"
      for p in "${path_array[@]}"; do
        PATH="$p:$PATH"
      done
    fi

    # Set project-specific environment variables
    if [[ -n "$project_env_vars_output" ]]; then
      IFS=$'\n' read -r -d '' -a env_array <<< "$project_env_vars_output"
      for env_line in "${env_array[@]}"; do
        if [[ "$env_line" =~ ^([^=]+)=(.*)$ ]]; then
          export "${BASH_REMATCH[1]}"="${BASH_REMATCH[2]}"
        fi
      done
    fi

    # Run validation (non-blocking)
    devscope &>/dev/null &
  else
    # If not in a DevScope project, reset PATH and ENV
    PATH="%s" # System PATH
    # Unset any project-specific env vars left over
    for env_var_name in $(compgen -v | grep '^DEVSCOPE_ENV_'); do
      unset "${env_var_name#DEVSCOPE_ENV_}"
    done
  fi
}

devscope_find_config() {
  local dir="$PWD"
  while [[ "$dir" != "/" && "$dir" != "" ]]; do
    if [[ -f "$dir/%s" ]]; then
      echo "$dir/%s"
      return 0
    fi
    dir=$(dirname "$dir")
  done
  return 1
}
`
)

// GenerateHookScript generates the shell script for ambient environment enforcement.
func GenerateHookScript(shellType string) (string, error) {
	// Add shell-env-paths and shell-env-vars commands to main.go before this works fully
	// For now, we'll generate a simplified script.
	// This will need expansion to be robust.

	// Placeholder for system PATH - in a real scenario, we would need to store/retrieve this.
	// For simplicity, we'll use a hardcoded value or assume the initial PATH is clean.
	// A more robust solution would snapshot PATH before DevScope modifies it.
	initialSystemPath := os.Getenv("PATH") // This is insufficient, ideally we'd get PATH before any DevScope influence.

	// The actual paths will be dynamic. For now, use placeholders.
	projectRootPlaceholder := "$(devscope_find_config | xargs dirname)"
	devscopeBinPlaceholder := "$project_root/.devscope/bin"
	devscopeToolsBinPlaceholder := "$project_root/.devscope/tools" // This needs to be built dynamically based on tools in config

	script := fmt.Sprintf(hookScriptTemplate,
		projectRootPlaceholder, devscopeBinPlaceholder, devscopeToolsBinPlaceholder,
		initialSystemPath,
		initialSystemPath,
		config.DevScopeConfigFileName, config.DevScopeConfigFileName,
	)

	// Shell-specific integration
	switch shellType {
	case "bash":
		script = strings.TrimSpace(script) + `
PROMPT_COMMAND="_devscope_chpwd_hook; $PROMPT_COMMAND"
`
	case "zsh":
		script = strings.TrimSpace(script) + `
add-zsh-hook chpwd _devscope_chpwd_hook
`
	default:
		return "", fmt.Errorf("unsupported shell type: %s. Only bash and zsh are supported.", shellType)
	}

	// For `shell-env-paths` and `shell-env-vars` commands. Add these to main.go `init()` or create new command files.
	// Add new commands to main.go for these CLI calls:
	// rootCmd.AddCommand(&cobra.Command{
	// 	Use: "shell-env-paths",
	// 	Run: func(cmd *cobra.Command, args []string) {
	// 		if paths, err := project.GetEnvironmentPaths(); err == nil {
	// 			for _, p := range paths { fmt.Println(p) }
	// 		}
	// 	},
	// })
	// rootCmd.AddCommand(&cobra.Command{
	// 	Use: "shell-env-vars",
	// 	Run: func(cmd *cobra.Command, args []string) {
	// 		if envs, err := project.GetEnvironmentVariables(); err == nil {
	// 			for k, v := range envs { fmt.Printf("%s=%s\n", k, v) }
	// 		}
	// 	},
	// })

	return script, nil
}
```

**`internal/tools/tool_manager.go`**

```go
package tools

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/devscope/devscope/internal/ui"
	"github.com/devscope/devscope/internal/util"
)

// ToolInstaller defines the interface for installing and checking tool versions.
type ToolInstaller interface {
	Name() string
	Install(version string, installDir string, binLinkDir string) error
	CheckVersion(version string, installDir string) error // installDir is where the tool *should* be
	GetVersion(installDir string) (string, error)         // gets the actual installed version
}

// ToolManager orchestrates tool installations and version checks.
type ToolManager struct{}

func NewToolManager() *ToolManager {
	return &ToolManager{}
}

// CheckToolVersion checks if the required tool version is installed at the expected location.
func (tm *ToolManager) CheckToolVersion(installer ToolInstaller, requiredVersion string) error {
	projectRoot, err := project.GetProjectRoot()
	if err != nil {
		return fmt.Errorf("could not determine project root: %w", err)
	}
	toolsDir, err := project.GetDevScopeToolsDirPath()
	if err != nil {
		return fmt.Errorf("could not determine tools directory: %w", err)
	}
	installDir := filepath.Join(toolsDir, installer.Name(), requiredVersion)

	if _, err := os.Stat(installDir); os.IsNotExist(err) {
		return fmt.Errorf("%s %s is not installed in %s", installer.Name(), requiredVersion, installDir)
	}

	installedVersion, err := installer.GetVersion(installDir)
	if err != nil {
		return fmt.Errorf("failed to get installed %s version: %w", installer.Name(), err)
	}

	if installedVersion != requiredVersion {
		return fmt.Errorf("installed %s version mismatch: expected %s, got %s", installer.Name(), requiredVersion, installedVersion)
	}

	return nil
}

// downloadAndExtract downloads a file from URL and extracts it to targetDir.
func downloadAndExtract(url, targetDir string) error {
	ui.Info(fmt.Sprintf("Downloading from %s...", url))
	archivePath, err := util.DownloadFile(targetDir, url)
	if err != nil {
		return fmt.Errorf("failed to download: %w", err)
	}
	defer os.Remove(archivePath) // Clean up the downloaded archive

	ui.Info(fmt.Sprintf("Extracting %s to %s...", filepath.Base(archivePath), targetDir))
	if strings.HasSuffix(archivePath, ".zip") {
		return util.Unzip(archivePath, targetDir)
	} else if strings.HasSuffix(archivePath, ".tar.gz") || strings.HasSuffix(archivePath, ".tgz") {
		return util.UntarGz(archivePath, targetDir)
	}
	return fmt.Errorf("unsupported archive type for %s", archivePath)
}
```

**`internal/tools/nodejs.go`**

```go
package tools

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"

	"github.com/devscope/devscope/internal/util"
)

// NodeJSInstaller implements ToolInstaller for Node.js
type NodeJSInstaller struct{}

func NewNodeJSInstaller() *NodeJSInstaller {
	return &NodeJSInstaller{}
}

func (n *NodeJSInstaller) Name() string {
	return "node"
}

func (n *NodeJSInstaller) Install(version string, installDir string, binLinkDir string) error {
	if _, err := os.Stat(filepath.Join(installDir, "bin", "node")); err == nil {
		// Already installed
		return n.CheckVersion(version, installDir)
	}

	osStr := runtime.GOOS
	archStr := runtime.GOARCH

	// Determine correct architecture string for Node.js downloads
	if archStr == "amd64" {
		archStr = "x64"
	} else if archStr == "arm64" && osStr == "darwin" {
		archStr = "arm64"
	} else if archStr == "arm64" && osStr == "linux" {
		archStr = "arm64" // Node.js often uses aarch64 for Linux ARM64
	}

	// Example URL format: https://nodejs.org/dist/v18.17.0/node-v18.17.0-darwin-x64.tar.gz
	downloadURL := fmt.Sprintf("https://nodejs.org/dist/v%s/node-v%s-%s-%s.tar.gz", version, version, osStr, archStr)

	if err := os.MkdirAll(installDir, 0755); err != nil {
		return fmt.Errorf("failed to create install directory %s: %w", installDir, err)
	}

	if err := downloadAndExtract(downloadURL, installDir); err != nil {
		return fmt.Errorf("failed to download and extract Node.js: %w", err)
	}

	// Node.js archives usually contain a top-level directory (e.g., node-v18.17.0-darwin-x64)
	// We need to move its contents to the installDir directly.
	extractedDir := filepath.Join(installDir, fmt.Sprintf("node-v%s-%s-%s", version, osStr, archStr))
	if _, err := os.Stat(extractedDir); err == nil {
		if err := util.MoveDirectoryContents(extractedDir, installDir); err != nil {
			return fmt.Errorf("failed to move extracted Node.js contents: %w", err)
		}
	}


	// Create symlinks in .devscope/bin
	nodeBinPath := filepath.Join(installDir, "bin", "node")
	npmBinPath := filepath.Join(installDir, "bin", "npm")
	npxBinPath := filepath.Join(installDir, "bin", "npx")

	if err := util.CreateOrUpdateSymlink(nodeBinPath, filepath.Join(binLinkDir, "node")); err != nil {
		return fmt.Errorf("failed to link node: %w", err)
	}
	if err := util.CreateOrUpdateSymlink(npmBinPath, filepath.Join(binLinkDir, "npm")); err != nil {
		return fmt.Errorf("failed to link npm: %w", err)
	}
	if err := util.CreateOrUpdateSymlink(npxBinPath, filepath.Join(binLinkDir, "npx")); err != nil {
		return fmt.Errorf("failed to link npx: %w", err)
	}


	return n.CheckVersion(version, installDir)
}

func (n *NodeJSInstaller) CheckVersion(version string, installDir string) error {
	installedVersion, err := n.GetVersion(installDir)
	if err != nil {
		return err
	}
	if installedVersion != version {
		return fmt.Errorf("expected node %s, but found %s", version, installedVersion)
	}
	return nil
}

func (n *NodeJSInstaller) GetVersion(installDir string) (string, error) {
	nodePath := filepath.Join(installDir, "bin", "node")
	if _, err := os.Stat(nodePath); os.IsNotExist(err) {
		return "", fmt.Errorf("node not found in %s", installDir)
	}

	cmd := exec.Command(nodePath, "--version")
	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("failed to get node version: %w", err)
	}
	return strings.TrimSpace(strings.TrimPrefix(string(output), "v")), nil
}

```

**`internal/tools/golang.go`** (Similar structure to `nodejs.go`)
**`internal/tools/python.go`** (Similar structure to `nodejs.go`, but usually uses `venv` or `pyenv`-like mechanisms for isolation, which DevScope would encapsulate)
**`internal/tools/clitool.go`** (More generic, handles custom URLs and binary names)

These will follow a similar pattern:
1.  `Name()`: returns "go", "python", or the custom CLI tool name.
2.  `Install()`:
    *   Checks if already installed.
    *   Constructs download URL based on OS/Arch and version.
    *   Calls `downloadAndExtract`.
    *   Handles specific extraction logic (e.g., Go creates a `go` directory, `kubectl` is a single binary).
    *   Creates symlinks in the `binLinkDir` (e.g., `.devscope/bin`).
3.  `CheckVersion()`: calls `GetVersion` and compares.
4.  `GetVersion()`: Executes `tool --version` or parses specific tool output.

**`internal/ui/output.go`**

```go
package ui

import (
	"fmt"

	"github.com/fatih/color"
)

var (
	successColor = color.New(color.FgGreen).SprintfFunc()
	infoColor    = color.New(color.FgCyan).SprintfFunc()
	warnColor    = color.New(color.FgYellow).SprintfFunc()
	errorColor   = color.New(color.FgRed).SprintfFunc()
)

// Success prints a success message.
func Success(format string, a ...interface{}) {
	fmt.Printf("%s %s\n", successColor("✓"), fmt.Sprintf(format, a...))
}

// Info prints an informational message.
func Info(format string, a ...interface{}) {
	fmt.Printf("%s %s\n", infoColor("➜"), fmt.Sprintf(format, a...))
}

// Warn prints a warning message.
func Warn(format string, a ...interface{}) {
	fmt.Printf("%s %s\n", warnColor("▲"), fmt.Sprintf(format, a...))
}

// Error prints an error message.
func Error(format string, a ...interface{}) {
	fmt.Printf("%s %s\n", errorColor("✗"), fmt.Sprintf(format, a...))
}
```

**`internal/util/filesystem.go`**

```go
package util

import (
	"archive/tar"
	"archive/zip"
	"compress/gzip"
	"fmt"
	"io"
	"os"
	"path/filepath"
)

// Unzip extracts a zip archive to the specified destination.
func Unzip(src, dest string) error {
	r, err := zip.OpenReader(src)
	if err != nil {
		return fmt.Errorf("failed to open zip file: %w", err)
	}
	defer r.Close()

	for _, f := range r.File {
		fpath := filepath.Join(dest, f.Name)

		if !strings.HasPrefix(fpath, filepath.Clean(dest)+string(os.PathSeparator)) {
			return fmt.Errorf("illegal file path: %s", fpath)
		}

		if f.FileInfo().IsDir() {
			os.MkdirAll(fpath, os.ModePerm)
			continue
		}

		if err = os.MkdirAll(filepath.Dir(fpath), os.ModePerm); err != nil {
			return err
		}

		outFile, err := os.OpenFile(fpath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.Mode())
		if err != nil {
			return err
		}

		rc, err := f.Open()
		if err != nil {
			return err
		}

		_, err = io.Copy(outFile, rc)

		outFile.Close()
		rc.Close()

		if err != nil {
			return err
		}
	}
	return nil
}

// UntarGz extracts a .tar.gz archive to the specified destination.
func UntarGz(src, dest string) error {
	file, err := os.Open(src)
	if err != nil {
		return fmt.Errorf("failed to open tar.gz file: %w", err)
	}
	defer file.Close()

	gzr, err := gzip.NewReader(file)
	if err != nil {
		return fmt.Errorf("failed to create gzip reader: %w", err)
	}
	defer gzr.Close()

	tr := tar.NewReader(gzr)

	for {
		header, err := tr.Next()
		if err == io.EOF {
			break // End of archive
		}
		if err != nil {
			return fmt.Errorf("failed to read tar header: %w", err)
		}

		target := filepath.Join(dest, header.Name)

		// Check for directory traversal
		if !strings.HasPrefix(target, filepath.Clean(dest)+string(os.PathSeparator)) {
			return fmt.Errorf("illegal file path: %s", target)
		}

		switch header.Typeflag {
		case tar.DIR:
			if err := os.MkdirAll(target, os.FileMode(header.Mode)); err != nil {
				return fmt.Errorf("failed to create directory %s: %w", target, err)
			}
		case tar.REGTYPE:
			if err := os.MkdirAll(filepath.Dir(target), os.FileMode(header.Mode)); err != nil {
				return fmt.Errorf("failed to create parent directory for %s: %w", target, err)
			}
			f, err := os.OpenFile(target, os.O_CREATE|os.O_RDWR, os.FileMode(header.Mode))
			if err != nil {
				return fmt.Errorf("failed to create file %s: %w", target, err)
			}
			if _, err := io.Copy(f, tr); err != nil {
				f.Close()
				return fmt.Errorf("failed to write file %s: %w", target, err)
			}
			f.Close()
		case tar.SYMLINK:
			// Handle symlinks
			if err := os.Symlink(header.Linkname, target); err != nil {
				return fmt.Errorf("failed to create symlink %s -> %s: %w", target, header.Linkname, err)
			}
		default:
			fmt.Printf("Skipping unknown type: %s, %c\n", header.Name, header.Typeflag)
		}
	}
	return nil
}

// CreateOrUpdateSymlink creates a symlink from oldname to newname. If newname already exists and is a symlink,
// it updates it. If it's a regular file/dir, it returns an error.
func CreateOrUpdateSymlink(oldname, newname string) error {
	// Ensure the directory for the symlink exists
	if err := os.MkdirAll(filepath.Dir(newname), 0755); err != nil {
		return fmt.Errorf("failed to create directory for symlink %s: %w", newname, err)
	}

	// Check if the symlink already exists
	if fi, err := os.Lstat(newname); err == nil {
		if fi.Mode()&os.ModeSymlink != 0 {
			// It's a symlink, check if it points to the correct location
			currentLinkTarget, err := os.Readlink(newname)
			if err != nil {
				return fmt.Errorf("failed to read existing symlink %s: %w", newname, err)
			}
			if currentLinkTarget == oldname {
				// Symlink is already correct, no need to update
				return nil
			}
			// Remove existing symlink to create a new one
			if err := os.Remove(newname); err != nil {
				return fmt.Errorf("failed to remove existing symlink %s: %w", newname, err)
			}
		} else {
			return fmt.Errorf("target path %s exists but is not a symlink; refusing to overwrite", newname)
		}
	} else if !os.IsNotExist(err) {
		return fmt.Errorf("failed to stat %s: %w", newname, err)
	}

	// Create the new symlink
	return os.Symlink(oldname, newname)
}

// MoveDirectoryContents moves all files and directories from src to dest.
// src directory will be removed after successful move.
func MoveDirectoryContents(src, dest string) error {
	entries, err := os.ReadDir(src)
	if err != nil {
		return fmt.Errorf("failed to read source directory %s: %w", src, err)
	}

	for _, entry := range entries {
		srcPath := filepath.Join(src, entry.Name())
		destPath := filepath.Join(dest, entry.Name())

		// Attempt to rename/move directly
		if err := os.Rename(srcPath, destPath); err != nil {
			// If rename fails, try copying (e.g., cross-device link)
			if !os.IsExist(err) { // If it's not "file exists", then it's a real rename error
				return fmt.Errorf("failed to rename %s to %s: %w", srcPath, destPath, err)
			}
			// If destPath exists, and it's a directory, we need to merge
			if entry.IsDir() {
				if err := os.MkdirAll(destPath, 0755); err != nil {
					return fmt.Errorf("failed to create destination directory for merge %s: %w", destPath, err)
				}
				if err := MoveDirectoryContents(srcPath, destPath); err != nil { // Recurse for directories
					return err
				}
			} else {
				return fmt.Errorf("failed to rename %s to %s: target exists %w", srcPath, destPath, err)
			}
		}
	}

	// Remove the source directory after moving its contents
	return os.RemoveAll(src)
}

// ErrorsToStrings converts a slice of errors to a slice of their string representations.
func ErrorsToStrings(errs []error) []string {
	var s []string
	for _, err := range errs {
		s = append(s, err.Error())
	}
	return s
}
```

**`internal/util/downloader.go`**

```go
package util

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/devscope/devscope/internal/ui"
)

// DownloadFile downloads a file from a given URL to a specified directory.
// It returns the path to the downloaded file.
func DownloadFile(destDir, url string) (string, error) {
	// Get the filename from the URL
	tokens := strings.Split(url, "/")
	filename := tokens[len(tokens)-1]
	if filename == "" {
		return "", fmt.Errorf("could not determine filename from URL: %s", url)
	}

	filePath := filepath.Join(destDir, filename)

	// Create the destination directory if it doesn't exist
	if err := os.MkdirAll(destDir, 0755); err != nil {
		return "", fmt.Errorf("failed to create destination directory %s: %w", destDir, err)
	}

	// Create the file
	out, err := os.Create(filePath)
	if err != nil {
		return "", fmt.Errorf("failed to create file %s: %w", filePath, err)
	}
	defer out.Close()

	// Get the data
	resp, err := http.Get(url)
	if err != nil {
		return "", fmt.Errorf("failed to download from %s: %w", url, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("bad status code for %s: %s", url, resp.Status)
	}

	// Write the body to file
	progressReader := &progressReader{
		Reader: resp.Body,
		total:  resp.ContentLength,
		name:   filename,
	}

	_, err = io.Copy(out, progressReader)
	if err != nil {
		return "", fmt.Errorf("failed to write downloaded file: %w", err)
	}

	ui.Info(fmt.Sprintf("Downloaded %s to %s", filename, filePath))
	return filePath, nil
}

// progressReader wraps an io.Reader to provide progress updates.
type progressReader struct {
	io.Reader
	total   int64 // Total bytes expected
	current int64 // Bytes read so far
	name    string
	lastP   int   // Last reported percentage
}

func (pr *progressReader) Read(p []byte) (n int, err error) {
	n, err = pr.Reader.Read(p)
	pr.current += int64(n)

	if pr.total > 0 {
		percentage := int(float64(pr.current) / float64(pr.total) * 100)
		if percentage%10 == 0 && percentage != pr.lastP { // Update every 10%
			ui.Info(fmt.Sprintf("Downloading %s: %d%% (%d/%d bytes)", pr.name, percentage, pr.current, pr.total))
			pr.lastP = percentage
		}
	} else if pr.current > 0 {
		// If total is unknown, just show bytes
		// For simplicity, we'll only show progress if total is known.
	}
	return
}
```
