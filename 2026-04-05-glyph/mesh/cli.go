package main

import (
	"flag"
	"fmt"
	"os"
)

type Commands struct {
	Init   bool
	Run    bool
	Prompt string
	Config string
}

func ParseCli() Commands {
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(1)
	}

	cmds := Commands{}

	switch os.Args[1] {
	case "init":
		cmds.Init = true
	case "run":
		cmds.Run = true
		runCmd := flag.NewFlagSet("run", flag.ExitOnError)
		configOpt := runCmd.String("config", "mesh.yml", "Path to config file")
		runCmd.Parse(os.Args[2:])
		cmds.Config = *configOpt
		args := runCmd.Args()
		if len(args) > 0 {
			cmds.Prompt = args[0]
		} else {
			fmt.Println("Error: run requires a prompt argument")
			os.Exit(1)
		}
	default:
		printUsage()
		os.Exit(1)
	}

	return cmds
}

func printUsage() {
	fmt.Println("mesh - docker-compose for local AI swarms")
	fmt.Println("Usage:")
	fmt.Println("  mesh init")
	fmt.Println("  mesh run <prompt> [--config mesh.yml]")
}
