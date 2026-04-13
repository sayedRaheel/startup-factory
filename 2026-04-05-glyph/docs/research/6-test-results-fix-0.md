**Root Cause Analysis:**
The build failed because the previous generator created a truncated, broken `test.sh` file. When the execution engine attempted to execute the rigorous compilation and integration test phase to validate the "Zero Vaporware Policy," it could not find the executable `test.sh` script. Furthermore, the previous script failed to actually run the compiler (`go build`) and verify the application logic. 

To fix this, I have rewritten the master builder script. It completely regenerates the application files (ensuring no `TODO`s or vaporware), scaffolds a robust `test.sh` file that strictly enforces compilation and binary execution, and then triggers the test suite.

```bash
#!/bin/bash
set -e

echo "==> Creating project directory 'mesh'..."
mkdir -p mesh
cd mesh

echo "==> Generating core Go application files..."

cat << 'EOF' > go.mod
module mesh

go 1.22

require gopkg.in/yaml.v3 v3.0.1
EOF

cat << 'EOF' > main.go
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
EOF

cat << 'EOF' > cli.go
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
EOF

cat << 'EOF' > config.go
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
				Command: "cat", // Default coder acts as pass-through pipe until overridden in mesh.yml
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
EOF

cat << 'EOF' > engine.go
package main

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
)

func ExecutePipeline(config *MeshConfig, initialPrompt string) error {
	currentPayload := initialPrompt

	fmt.Printf("🚀 Starting Mesh Pipeline: %s\n\n", config.Name)

	for _, step := range config.Pipeline {
		fmt.Printf("⚙️  Running Agent: [%s]\n", step.Name)

		cmd := exec.Command("sh", "-c", step.Command)

		cmd.Env = os.Environ()
		for k, v := range step.Env {
			cmd.Env = append(cmd.Env, fmt.Sprintf("%s=%s", k, v))
		}

		cmd.Stdin = bytes.NewBufferString(currentPayload)
		cmd.Stderr = os.Stderr

		output, err := cmd.Output()
		if err != nil {
			return fmt.Errorf("agent [%s] failed: %w", step.Name, err)
		}

		currentPayload = string(output)
	}

	fmt.Printf("\n✅ Pipeline complete. Final Output:\n\n%s\n", currentPayload)
	return nil
}
EOF

echo "==> Generating rigorous test.sh compiler and executor..."
cat << 'EOF' > test.sh
#!/bin/bash
set -e

echo "-----------------------------------"
echo "🛠️  Fetching Dependencies & Building Binary..."
echo "-----------------------------------"
go mod tidy
go build -o mesh
echo "✅ Compilation successful."

echo "-----------------------------------"
echo "🧪 Running Unit/Integration Tests..."
echo "-----------------------------------"

# Ensure pristine testing state
rm -f mesh.yml

echo "Test 1: 'mesh init' creates config file"
./mesh init
if [ ! -f "mesh.yml" ]; then
    echo "❌ ERROR: mesh init failed to create mesh.yml"
    exit 1
fi
echo "✅ Test 1 Passed: mesh.yml created."

echo "Test 2: 'mesh run' executes pipeline successfully"
OUTPUT=$(./mesh run "Test Prompt: Build a simple API")

if echo "$OUTPUT" | grep -q "Pipeline complete"; then
    echo "✅ Test 2 Passed: Pipeline executed."
else
    echo "❌ ERROR: Pipeline execution failed or returned unexpected output."
    echo "Output received:"
    echo "$OUTPUT"
    exit 1
fi

echo "Test 3: 'mesh run' with missing prompt fails correctly"
if ./mesh run >/dev/null 2>&1; then
    echo "❌ ERROR: 'mesh run' should have failed without a prompt, but it succeeded."
    exit 1
else
    echo "✅ Test 3 Passed: Caught missing prompt error."
fi

echo "-----------------------------------"
echo "🎉 ALL TESTS PASSED SUCCESSFULLY!"
echo "-----------------------------------"
EOF

chmod +x test.sh

echo "==> Executing test script natively to enforce Zero Vaporware Policy..."
./test.sh
```
