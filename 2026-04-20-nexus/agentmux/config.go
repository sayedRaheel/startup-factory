package main

import (
	"os"

	"gopkg.in/yaml.v3"
)

type Endpoint struct {
	URL     string `yaml:"url"`
	AuthEnv string `yaml:"auth_env,omitempty"`
}

type Route struct {
	Path     string    `yaml:"path"`
	Primary  Endpoint  `yaml:"primary"`
	Fallback *Endpoint `yaml:"fallback,omitempty"`
}

type Config struct {
	Port   int     `yaml:"port"`
	Routes []Route `yaml:"routes"`
}

func LoadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}
	return &cfg, nil
}
