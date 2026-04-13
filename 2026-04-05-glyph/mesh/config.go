package main

import (
	"fmt"
	"os"

	"gopkg.in/yaml.v3"
)

type Step struct {
	Name    string            `yaml:"name"`
	Command string            `yaml:"command"`
	Env     map[string]string `yaml:"env"`
}

type MeshConfig struct {
	Name     string `yaml:"name"`
	Pipeline []Step `yaml:"pipeline"`
}

func DefaultConfig() MeshConfig {
	return MeshConfig{
		Name: "default-swarm",
		Pipeline: []Step{
			{
				Name:    "architect",
				Command: "echo 'Translating prompt to architecture...'",
				Env:     make(map[string]string),
			},
			{
				Name:    "coder",
				Command: "cat", // In reality, this would be `ollama run codellama`
			},
		},
	}
}

func LoadConfig(path string) (*MeshConfig, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file. Did you run 'mesh init'? Error: %w", err)
	}
	var config MeshConfig
	if err := yaml.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("invalid YAML format: %w", err)
	}
	return &config, nil
}
