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
