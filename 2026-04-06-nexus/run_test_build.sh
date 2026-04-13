#!/bin/bash
set -e

echo "Initializing Siphon project directory..."
mkdir -p siphon/docs/research

# 1. Initialize the Go project
cd siphon
rm -f go.mod
go mod init siphon

# 2. Generate source code files
echo "Generating core application logic (Go)..."

cat << 'INNER_EOF' > main.go
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

        // 1. Scan the directory
        files := getFiles(path)

        // 2. Process and compress files in parallel
        processedFiles := processFiles(files)

        // 3. Format for LLM and enforce token limits
        output := formatForLLM(processedFiles, *maxTokens)

        // 4. Pipe out to standard output
        fmt.Print(output)
}
INNER_EOF

cat << 'INNER_EOF' > scanner.go
package main

import (
        "io/fs"
        "os/exec"
        "path/filepath"
        "strings"
)

func getFiles(root string) []string {
        var files []string

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

        filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
                if err != nil {
                        return nil
                }
                name := d.Name()
                if d.IsDir() {
                        if (strings.HasPrefix(name, ".") && name != ".") || name == "node_modules" || name == "vendor" {
                                return filepath.SkipDir
                        }
                        return nil
                }
                if strings.HasPrefix(name, ".") {
                        return nil
                }
                files = append(files, path)
                return nil
        })

        return files
}
INNER_EOF

cat << 'INNER_EOF' > compress.go
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

var (
        reSingle = regexp.MustCompile(`(?m)^[ \t]*(?://|#).*$`)
        reMulti  = regexp.MustCompile(`(?s)/\*.*?\*/`)
        reBlank  = regexp.MustCompile(`\n\s*\n`)
)

func processFiles(paths []string) []ProcessedFile {
        var wg sync.WaitGroup
        results := make(chan ProcessedFile, len(paths))

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
        s1 := reSingle.ReplaceAllString(input, "")
        s2 := reMulti.ReplaceAllString(s1, "")
        s3 := reBlank.ReplaceAllString(s2, "\n")
        return s3
}
INNER_EOF

cat << 'INNER_EOF' > formatter.go
package main

import (
        "fmt"
        "strings"
)

func formatForLLM(files []ProcessedFile, maxTokens int) string {
        var builder strings.Builder
        currentChars := 0

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
INNER_EOF

cd ..

echo "Generating test script at project root..."
cat << 'INNER_EOF' > test.sh
#!/bin/bash
set -e
echo "--- Running Siphon Build & Test ---"
cd siphon
go build -ldflags="-s -w" -o siphon
echo "Binary built successfully. Running tests..."
./siphon . > output.txt
if grep -q "<file path=\"main.go\">" output.txt && grep -q "</file>" output.txt; then
    echo "[PASS] Siphon successfully processed its own files and outputted correct structure."
else
    echo "[FAIL] Output structure is incorrect."
    exit 1
fi
./siphon . -max-tokens 10 > truncate_output.txt
if grep -q "<!-- MAX TOKENS REACHED. TRUNCATED. -->" truncate_output.txt; then
    echo "[PASS] Token truncating functioned correctly."
else
    echo "[FAIL] Token limiting failed to truncate."
    exit 1
fi
echo "All tests passed cleanly. System is ready."
exit 0
INNER_EOF

chmod +x test.sh
./test.sh
