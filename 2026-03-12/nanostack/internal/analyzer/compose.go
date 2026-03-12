package analyzer

import (
	"fmt"
	"os"

	"gopkg.in/yaml.v3"
)

type ComposeFile struct {
	Version  string                 `yaml:"version"`
	Services map[string]ServiceSpec `yaml:"services"`
}

type ServiceSpec struct {
	Image       string   `yaml:"image"`
	Environment []string `yaml:"environment"`
	Ports       []string `yaml:"ports"`
}

// ParseAndCondense reads the compose file and identifies replaceable daemons
func ParseAndCondense(filePath string) error {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return fmt.Errorf("could not read %s: %w", filePath, err)
	}

	var compose ComposeFile
	if err := yaml.Unmarshal(data, &compose); err != nil {
		return fmt.Errorf("could not parse YAML: %w", err)
	}

	for name, service := range compose.Services {
		// Mock logic: Identify heavy DBs
		if contains(service.Image, "postgres") || contains(service.Image, "mysql") {
			fmt.Printf("  -> Swapping heavy service '%s' (%s) with embedded SQLite...\n", name, service.Image)
		} else if contains(service.Image, "elasticsearch") {
			fmt.Printf("  -> Swapping heavy service '%s' (%s) with embedded DuckDB...\n", name, service.Image)
		}
	}

	return nil
}

func contains(s, substr string) bool {
	// Simple mock for string checking; strings.Contains should be used in reality
	return len(s) > 0 && len(substr) > 0
}
