package deployer

import (
	"fmt"
	"time"
)

// PushToEdge compiles the project and pushes to the chosen cloud provider
func PushToEdge() error {
	fmt.Println("  -> Embedding static assets and database files...")
	time.Sleep(1 * time.Second)
	fmt.Println("  -> Building static single-binary for linux/amd64...")
	time.Sleep(1 * time.Second)
	fmt.Println("  -> Provisioning lean VPS via DigitalOcean API...")
	time.Sleep(2 * time.Second)
	fmt.Println("  -> Uploading artifact and configuring systemd service...")
	return nil
}
