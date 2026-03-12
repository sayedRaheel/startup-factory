package runner

import (
	"fmt"
	"time"
)

// StartNativeServer mimics starting the proxy/monolith locally without Docker
func StartNativeServer() error {
	fmt.Println("  -> Binding local ports...")
	fmt.Println("  -> Mounting embedded SQLite/DuckDB volumes...")
	fmt.Println("  -> Server listening on http://localhost:8080 (Press Ctrl+C to stop)")
	
	// Keep process alive for dev simulation
	for {
		time.Sleep(1 * time.Second)
	}
}
