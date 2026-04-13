package main

import (
	"fmt"
	"os"

	"gopkg.in/yaml.v3"
)

func main() {
	cmds := ParseCli()

	if cmds.Init {
		cfg := DefaultConfig()
		data, err := yaml.Marshal(&cfg)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error generating yaml: %v\n", err)
			os.Exit(1)
		}
		err = os.WriteFile("mesh.yml", data, 0644)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error writing mesh.yml: %v\n", err)
			os.Exit(1)
		}
		fmt.Println("✅ Created mesh.yml. You are ready to build the swarm.")
		return
	}

	if cmds.Run {
		cfg, err := LoadConfig(cmds.Config)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error loading config: %v\n", err)
			os.Exit(1)
		}
		err = ExecutePipeline(cfg, cmds.Prompt)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Pipeline error: %v\n", err)
			os.Exit(1)
		}
	}
}
