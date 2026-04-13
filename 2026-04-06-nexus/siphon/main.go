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
