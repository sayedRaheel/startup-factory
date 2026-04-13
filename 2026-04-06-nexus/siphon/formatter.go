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
