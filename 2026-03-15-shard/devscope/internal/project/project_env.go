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

		if err := toolManager.CheckToolVersion(installer, toolCfg.Version); err != nil {
			toolErrors = append(toolErrors, fmt.Errorf("%s %s required: %w", toolName, toolCfg.Version, err))
		} else {
			ui.Success(fmt.Sprintf("%s %s is consistent.", toolName, toolCfg.Version))
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
		} else {
			ui.Success(fmt.Sprintf("Environment variable '%s' is consistent.", key))
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
		// Check if the bin directory for the tool actually exists
		if _, err := os.Stat(toolBinPath); err == nil {
			paths = append(paths, toolBinPath)
		} else if !os.IsNotExist(err) {
			// Report other errors than "not exist"
			return nil, fmt.Errorf("failed to check tool bin path %s: %w", toolBinPath, err)
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
