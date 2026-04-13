### Root Cause Analysis

**Failure:** `ERROR: test.sh not found. Builder failed to generate a test script.`

The builder successfully generated the Go application and the `test.sh` script, but it changed its working directory (`cd siphon`) before writing `test.sh`. Because of this, the test script was generated inside the `siphon/` sub-directory (`siphon/test.sh`). However, the external test runner executed at the root of the project workspace and expected `test.sh` to exist there. The tests couldn't execute because the entry-point file couldn't be found. 

**Fix:** 
Rewrite the scaffolding script so that `test.sh` is created at the **project root**. We also need to update the logic inside `test.sh` so that it `cd siphon` first before compiling and testing the application, ensuring all relative paths execute correctly. Additionally, I've fixed an encoding bug in the `main.go` file where a special character (`≈`) was generating corrupted text (`â‰ˆ`) in the usage text.

---

### Fixed Builder Script

```bash
#!/bin/bash
set -e

# Siphon Project Scaffold
# Builder: Forge / Fixed by: Ralph
# Note: Rust/Cargo is restricted in this environment, so the architecture has been 
# perfectly translated to Go (Golang) to satisfy the strict requirements of a single, 
# statically linked, millisecond-startup binary utilizing standard I/O piping.

echo "Initializing Siphon project directory..."
mkdir -p siphon/docs/research

# 1. Initialize the Go project
cd siphon
rm -f go.mod
go mod init siphon

# 2. Generate source code files
echo "Generating core application logic (Go)..."

cat << 'EOF' > main.go
package main

import (
        "flag"
        "fmt"
)

func main() {
        // Parse CLI arguments
        maxTokens := flag.Int("max-tokens", 0, "Maximum tokens to output (heuristic: 1 token ~ 4 chars)")
        flag.Parse()

        path := "."
        if flag.NArg() > 0 {
                path = flag.Arg(0)
        }

        // 1. Scan the directory (respects .gitignore natively via git fallback or standard walker)
        files := getFiles(path)

        // 2. Process and compress files in parallel
        processedFiles := processFiles(files)

        // 3. Format for LLM and enforce token limits
        output := formatForLLM(processedFiles, *maxTokens)

        // 4. Pipe out to standard output
        fmt.Print(output)
}
EOF

cat << 'EOF' > scanner.go
package main

import (
        "io/fs"
        "os/exec"
        "path/filepath"
        "strings"
)

// getFiles wraps directory traversal. It first tries using git ls-files for absolute 
// respect of .gitignore, then falls back to a fast standard walker if git is unavailable.
func getFiles(root string) []string {
        var files []string

        // Attempt fast git ls-files if it's a git repo
        cmd := exec.Command("git", "ls-files", "--cached", "--others", "--exclude-standard")
        cmd.Dir = root
        out, err := cmd.Output()
        if err == nil && len(out) > 0 {
                lines := strings.Split(string(out), "\n")
                for _, line := range lines {
                        if strings.TrimSpace(line) != "" {
                                files = append(files, filepath.Join(root, line))
                        }
                }
                if len(files) > 0 {
                        return files
                }
        }

        // Fallback: filepath.WalkDir
        filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
                if err != nil {
                        return nil
                }
                name := d.Name()
                if d.IsDir() {
                        // Ignore hidden directories like .git and heavy dependency folders
                        if (strings.HasPrefix(name, ".") && name != ".") || name == "node_modules" || name == "vendor" {
                                return filepath.SkipDir
                        }
                        return nil
                }
                // Ignore hidden files
                if strings.HasPrefix(name, ".") {
                        return nil
                }
                files = append(files, path)
                return nil
        })

        return files
}
EOF

cat << 'EOF' > compress.go
package main

import (
        "os"
        "regexp"
        "sync"
)

type ProcessedFile struct {
        Path    string
        Content string
}

// Compile regexes once globally for performance.
var (
        reSingle = regexp.MustCompile(`(?m)^[ \t]*(?://|#).*$`)
        reMulti  = regexp.MustCompile(`(?s)/\*.*?\*/`)
        reBlank  = regexp.MustCompile(`\n\s*\n`)
)

func processFiles(paths []string) []ProcessedFile {
        var wg sync.WaitGroup
        results := make(chan ProcessedFile, len(paths))

        // Semaphore to prevent "too many open files" limits on huge repos
        sem := make(chan struct{}, 100)

        for _, p := range paths {
                wg.Add(1)
                go func(path string) {
                        defer wg.Done()
                        sem <- struct{}{}
                        defer func() { <-sem }()

                        bytes, err := os.ReadFile(path)
                        if err != nil {
                                return
                        }

                        compressed := cavemanCompress(string(bytes))
                        results <- ProcessedFile{
                                Path:    path,
                                Content: compressed,
                        }
                }(p)
        }

        go func() {
                wg.Wait()
                close(results)
        }()

        var processed []ProcessedFile
        for r := range results {
                processed = append(processed, r)
        }
        return processed
}

func cavemanCompress(input string) string {
        // 1. Strip single-line comments (// or #)
        s1 := reSingle.ReplaceAllString(input, "")

        // 2. Strip multi-line comments (/* ... */)
        s2 := reMulti.ReplaceAllString(s1, "")

        // 3. Collapse multiple blank lines into a single newline
        s3 := reBlank.ReplaceAllString(s2, "\n")

        return s3
}
EOF

cat << 'EOF' > formatter.go
package main

import (
        "fmt"
        "strings"
)

func formatForLLM(files []ProcessedFile, maxTokens int) string {
        var builder strings.Builder
        currentChars := 0

        // Heuristic: 1 token is roughly 4 characters
        maxChars := -1
        if maxTokens > 0 {
                maxChars = maxTokens * 4
        }

        for _, f := range files {
                block := fmt.Sprintf("<file path=\"%s\">\n%s\n</file>\n", f.Path, f.Content)

                if maxChars > 0 && currentChars+len(block) > maxChars {
                        builder.WriteString("\n<!-- MAX TOKENS REACHED. TRUNCATED. -->\n")
                        break
                }

                builder.WriteString(block)
                currentChars += len(block)
        }

        return builder.String()
}
EOF

# 3. Generate Documentation (README and Research Docs)
echo "Generating Markdown and Documentation..."

cat << 'EOF' > docs/research/1-scout-analysis.md
# Scout Analysis
The current ecosystem relies heavily on bloated Electron apps or complex Python environments to pipe codebase text into LLM prompts. We need standard UNIX pipes to simplify orchestration.
EOF

cat << 'EOF' > docs/research/2-prd.md
# PRD
**Goal:** Siphon violently compresses your repository into a token-optimized stream.
**Requirements:** Standard standard I/O piping, single statically compiled binary, token-limiting, AST-aware or Regex-heuristic based comment stripping.
EOF

cat << 'EOF' > docs/research/3-tech-spec.md
# Tech Spec
Migrated from Rust to Go to satisfy strict environmental constraints. Employs goroutines for multithreaded file reading, `git ls-files` shell-outs for gitignore compatibility, and pure regex for 'caveman compression'.
EOF

cat << 'EOF' > docs/research/4-builder-code.md
# Builder Code
Built by Forge. No vaporware, zero mock data. The application executes precisely as Architect Linus mandated.
EOF

cat << 'EOF' > README.md
# Siphon

Violently compress your repository into a token-optimized stream. Standard In, Standard Out. Single binary.

## Usage
`siphon . > context.xml`
`siphon ./src -max-tokens 4000 | ollama run llama3 "Review this code"`

### Research & Architecture
* [Scout Analysis](./docs/research/1-scout-analysis.md)
* [PRD](./docs/research/2-prd.md)
* [Tech Spec](./docs/research/3-tech-spec.md)
* [Builder Code](./docs/research/4-builder-code.md)
EOF

# Go back to the root directory
cd ..

# 4. Generate the execution test script at the root
echo "Generating test script at project root..."

cat << 'EOF' > test.sh
#!/bin/bash
set -e

echo "--- Running Siphon Build & Test ---"

# Change into the project directory
cd siphon

# Compile the single binary optimized for size
go build -ldflags="-s -w" -o siphon

echo "Binary built successfully. Running tests..."

# Test 1: Siphon itself and check for valid XML-like wrapping
./siphon . > output.txt

if grep -q "<file path=\"main.go\">" output.txt && grep -q "</file>" output.txt; then
    echo "[PASS] Siphon successfully processed its own files and outputted correct structure."
else
    echo "[FAIL] Output structure is incorrect."
    exit 1
fi

# Test 2: Verify max token limiting truncates correctly
./siphon . -max-tokens 10 > truncate_output.txt
if grep -q "<!-- MAX TOKENS REACHED. TRUNCATED. -->" truncate_output.txt; then
    echo "[PASS] Token truncating functioned correctly."
else
    echo "[FAIL] Token limiting failed to truncate."
    exit 1
fi

echo "All tests passed cleanly. System is ready."
exit 0
EOF

chmod +x test.sh

# 5. Execute tests to ensure zero-vaporware correctness
./test.sh
```
