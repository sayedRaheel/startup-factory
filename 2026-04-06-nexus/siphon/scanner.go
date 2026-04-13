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
