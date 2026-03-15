package config

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"
)

const DevScopeConfigFileName = "devscope.yaml"

// DevScopeConfig represents the structure of the devscope.yaml file
type DevScopeConfig struct {
	Tools map[string]ToolConfig `yaml:"tools"`
	Env   map[string]string     `yaml:"env"`
}

// ToolConfig defines a generic tool configuration.
type ToolConfig struct {
	Version string                `yaml:"version,omitempty"`
	URL     string                `yaml:"url,omitempty"`     // For CLI tools with custom download URLs
	Binary  string                `yaml:"binary,omitempty"`  // For CLI tools, expected binary name post-extraction
	Args    []string              `yaml:"args,omitempty"`    // Additional args for installation scripts (future)
	Nested  map[string]ToolConfig `yaml:",inline"`           // For nesting, like 'cli' containing 'kubectl'
}

// ParseConfig reads and parses the devscope.yaml file from the given path.
func ParseConfig(configPath string) (*DevScopeConfig, error) {
	data, err := os.ReadFile(configPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read %s: %w", DevScopeConfigFileName, err)
	}

	// Use an intermediate struct to handle the 'cli' nesting before flattening
	var rawCfg struct {
		Tools map[string]ToolConfig `yaml:"tools"`
		Env   map[string]string     `yaml:"env"`
	}
	if err := yaml.Unmarshal(data, &rawCfg); err != nil {
		return nil, fmt.Errorf("failed to parse %s: %w", DevScopeConfigFileName, err)
	}

	cfg := &DevScopeConfig{
		Tools: make(map[string]ToolConfig),
		Env:   rawCfg.Env,
	}

	for toolName, toolCfg := range rawCfg.Tools {
		if strings.ToLower(toolName) == "cli" {
			// Process nested CLI tools under the 'cli' key
			for cliToolName, nestedToolCfg := range toolCfg.Nested {
				if _, exists := cfg.Tools[cliToolName]; exists {
					return nil, fmt.Errorf("duplicate tool definition: '%s' found both as top-level and under 'cli'", cliToolName)
				}
				cfg.Tools[cliToolName] = nestedToolCfg
			}
		} else {
			cfg.Tools[toolName] = toolCfg
		}
	}

	return cfg, nil
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
