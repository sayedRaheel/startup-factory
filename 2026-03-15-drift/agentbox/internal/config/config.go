package config

import (
	"gopkg.in/yaml.v3"
	"os"
)

type Config struct {
	Whitelist Whitelist `yaml:"whitelist"`
}

type Whitelist struct {
	Commands []string `yaml:"commands"`
	Paths    []string `yaml:"paths"`
	EnvVars  []string `yaml:"env_vars"`
}

func LoadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var cfg Config
	err = yaml.Unmarshal(data, &cfg)
	if err != nil {
		return nil, err
	}
	return &cfg, nil
}

func CreateDefaultConfig(path string) error {
	defaultCfg := `whitelist:
  commands:
    - "python"
    - "node"
    - "ls"
    - "echo"
  paths:
    - "./data"
    - "./output"
  env_vars:
    - "OPENAI_API_KEY"
`
	return os.WriteFile(path, []byte(defaultCfg), 0644)
}
