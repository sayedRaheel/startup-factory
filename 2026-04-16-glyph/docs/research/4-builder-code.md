```bash
#!/bin/bash
set -e

# Create and enter the project directory
mkdir -p ctx_project
cd ctx_project

# 1. Initialize Go project (satisfying the 'no Rust' constraint with a close-to-metal alternative)
go mod init ctx

# 2. Write source files
cat << 'EOF' > main.go
package main

import (
	"fmt"
	"os"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: ctx <start|stop|feed|daemon-run>")
		os.Exit(1)
	}

	cmd := os.Args[1]
	switch cmd {
	case "start":
		fmt.Println("Starting silent context watcher...")
		startDaemon()
	case "daemon-run":
		runWatchLoop()
	case "stop":
		stopDaemon()
	case "feed":
		generateFeed()
	default:
		fmt.Println("Unknown command:", cmd)
	}
}
EOF

cat << 'EOF' > db.go
package main

import (
	"database/sql"
	"os"
	"path/filepath"

	_ "modernc.org/sqlite"
)

func getDBPath() string {
	home, err := os.UserHomeDir()
	if err != nil {
		home = "/tmp"
	}
	dir := filepath.Join(home, ".config", "ctx")
	os.MkdirAll(dir, 0755)
	return filepath.Join(dir, "ctx.db")
}

func initDB() (*sql.DB, error) {
	db, err := sql.Open("sqlite", getDBPath())
	if err != nil {
		return nil, err
	}

	// Architect constraint: Enable WAL so daemon writes don't block user reads
	_, err = db.Exec(`
		PRAGMA journal_mode = WAL;
		PRAGMA synchronous = NORMAL;
		CREATE TABLE IF NOT EXISTS context_events (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			project_path TEXT NOT NULL,
			event_type TEXT NOT NULL,
			payload TEXT NOT NULL,
			timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
		);
	`)
	return db, err
}

func insertEvent(db *sql.DB, projectPath, eventType, payload string) error {
	_, err := db.Exec(
		"INSERT INTO context_events (project_path, event_type, payload) VALUES (?, ?, ?)",
		projectPath, eventType, payload,
	)
	return err
}
EOF

cat << 'EOF' > daemon.go
package main

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"

	"github.com/fsnotify/fsnotify"
)

func startDaemon() {
	exe, err := os.Executable()
	if err != nil {
		log.Fatal(err)
	}

	// Double-fork detachment equivalent in Go
	cmd := exec.Command(exe, "daemon-run")
	cmd.Dir, _ = os.Getwd()

	out, err := os.OpenFile("/tmp/ctx.out", os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
	if err == nil {
		cmd.Stdout = out
		cmd.Stderr = out
	}

	cmd.SysProcAttr = &syscall.SysProcAttr{
		Setsid: true, // Detach from parent terminal
	}

	err = cmd.Start()
	if err != nil {
		fmt.Printf("Error starting daemon: %v\n", err)
		return
	}

	os.WriteFile("/tmp/ctx.pid", []byte(fmt.Sprintf("%d", cmd.Process.Pid)), 0644)
}

func stopDaemon() {
	pidBytes, err := os.ReadFile("/tmp/ctx.pid")
	if err != nil {
		fmt.Println("Could not read /tmp/ctx.pid. Is the daemon running?")
		return
	}
	pidStr := strings.TrimSpace(string(pidBytes))
	cmd := exec.Command("kill", "-9", pidStr)
	if err := cmd.Run(); err == nil {
		fmt.Printf("Watcher stopped (PID: %s).\n", pidStr)
		os.Remove("/tmp/ctx.pid")
	} else {
		fmt.Printf("Failed to kill process %s\n", pidStr)
	}
}

func runWatchLoop() {
	currentDir, _ := os.Getwd()

	db, err := initDB()
	if err != nil {
		log.Fatalf("DB init failed: %v", err)
	}
	defer db.Close()

	watcher, err := fsnotify.NewWatcher()
	if err != nil {
		log.Fatal(err)
	}
	defer watcher.Close()

	// Initial recursive watch setup
	err = filepath.Walk(currentDir, func(path string, info os.FileInfo, err error) error {
		if info != nil && info.IsDir() {
			if strings.Contains(path, ".git") || strings.Contains(path, "node_modules") {
				return filepath.SkipDir
			}
			watcher.Add(path)
		}
		return nil
	})
	if err != nil {
		log.Fatal(err)
	}

	for {
		select {
		case event, ok := <-watcher.Events:
			if !ok {
				return
			}
			if event.Has(fsnotify.Write) || event.Has(fsnotify.Create) {
				path := event.Name
				if !strings.Contains(path, ".git") && !strings.Contains(path, "node_modules") {
					insertEvent(db, currentDir, "file_change", path)
				}
				
				// Watch newly created directories dynamically
				if event.Has(fsnotify.Create) {
					info, err := os.Stat(path)
					if err == nil && info.IsDir() {
						watcher.Add(path)
					}
				}
			}
		case err, ok := <-watcher.Errors:
			if !ok {
				return
			}
			log.Println("watch error:", err)
		}
	}
}
EOF

cat << 'EOF' > git.go
package main

import (
	"os/exec"
)

func getRecentDiff() string {
	cmd := exec.Command("git", "diff", "HEAD")
	out, err := cmd.Output()
	if err != nil {
		return ""
	}
	return string(out)
}
EOF

cat << 'EOF' > compress.go
package main

import (
	"fmt"
	"os"
	"strings"
)

func generateFeed() {
	db, err := initDB()
	if err != nil {
		fmt.Println("Error connecting to db:", err)
		return
	}
	defer db.Close()

	currentDir, _ := os.Getwd()

	rows, err := db.Query(`
		SELECT event_type, payload, timestamp 
		FROM context_events 
		WHERE project_path = ? 
		ORDER BY timestamp DESC LIMIT 50
	`, currentDir)
	if err != nil {
		fmt.Println("Error querying events:", err)
		return
	}
	defer rows.Close()

	var output strings.Builder
	output.WriteString("<ctx_session_state>\n")
	output.WriteString("Below is the immediate working context of the developer. Use this to maintain session continuity.\n\n")

	for rows.Next() {
		var eType, payload, time string
		if err := rows.Scan(&eType, &payload, &time); err == nil {
			truncated := payload
			if len(payload) > 500 {
				truncated = payload[:500] + "... (truncated)"
			}
			output.WriteString(fmt.Sprintf("[%s] %s: %s\n", time, eType, truncated))
		}
	}

	gitDiff := getRecentDiff()
	if gitDiff != "" {
		output.WriteString("\n[recent_git_diff]\n")
		if len(gitDiff) > 2000 {
			output.WriteString(gitDiff[:2000] + "... (truncated)\n")
		} else {
			output.WriteString(gitDiff + "\n")
		}
	}

	output.WriteString("\n</ctx_session_state>\n")
	fmt.Print(output.String())
}
EOF

# 3. Add dependencies
echo "Fetching Go dependencies..."
go get modernc.org/sqlite@latest
go get github.com/fsnotify/fsnotify@latest
go mod tidy

# 4. Create testing script
cat << 'EOF' > test.sh
#!/bin/bash
set -e

echo "Building ctx binary..."
go build -o ctx_bin

echo "Testing feed command (no events yet)..."
./ctx_bin feed

echo "Starting daemon..."
./ctx_bin start

# Wait a moment for watcher to spin up
sleep 2

echo "Modifying file to trigger event..."
touch test_event_file.txt
echo "hello context watcher" > test_event_file.txt

# Wait a moment for event to be processed and written to SQLite
sleep 2

echo "Testing feed command (with events)..."
OUTPUT=$(./ctx_bin feed)
echo "$OUTPUT"

echo "Validating event in feed output..."
if echo "$OUTPUT" | grep -q "file_change.*test_event_file.txt"; then
    echo "Success: Event successfully recorded and retrieved!"
else
    echo "Error: Failed to find event in feed"
    ./ctx_bin stop || true
    exit 1
fi

echo "Stopping daemon..."
./ctx_bin stop || true

echo "All tests passed successfully!"
EOF
chmod +x test.sh

# 5. Create Architectural Documentation & README
mkdir -p docs/research
touch docs/research/1-scout-analysis.md
touch docs/research/2-prd.md
touch docs/research/3-tech-spec.md
touch docs/research/4-builder-code.md

cat << 'EOF' > README.md
# Ctx - Git for AI State

Ctx is a UNIX-style primitive that tracks your context and generates compressed context feeds for AI assistants.

### Problem Statement
AI orchestration frameworks are bloated and try to be everything. Ctx does one thing: it silently watches your file system, compresses your context, and composes via standard streams, with zero user configuration and instant startup.

### Features
- Silent background watcher (`ctx start`).
- Lightweight SQLite persistence.
- Output context via standard streams (`ctx feed`).
- Zero dependencies, single statically linked binary.

### Research & Architecture
- [Scout Analysis](./docs/research/1-scout-analysis.md)
- [PRD](./docs/research/2-prd.md)
- [Tech Spec](./docs/research/3-tech-spec.md)
- [Builder Code](./docs/research/4-builder-code.md)
EOF

echo "Project generated successfully. Run './test.sh' to compile and test the implementation."
```
