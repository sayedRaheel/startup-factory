package tools

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/devscope/devscope/internal/ui"
	"github.com/devscope/devscope/internal/util"
)

// GolangInstaller implements ToolInstaller for Go
type GolangInstaller struct{}

func NewGolangInstaller() *GolangInstaller {
	return &GolangInstaller{}
}

func (g *GolangInstaller) Name() string {
	return "go"
}

func (g *GolangInstaller) Install(version string, installDir string, binLinkDir string) error {
	// Check if Go is already installed at the target location
	goBinPath := filepath.Join(installDir, "bin", "go")
	if _, err := os.Stat(goBinPath); err == nil {
		// If it exists, check its version
		if err := g.CheckVersion(version, installDir); err == nil {
			return nil // Correct version already installed
		}
		ui.Info(fmt.Sprintf("Go %s found, but not version %s. Reinstalling...", g.GetVersion(installDir), version))
		os.RemoveAll(installDir) // Clean up old installation
	}

	osStr := runtime.GOOS
	archStr := runtime.GOARCH

	// Go uses 'amd64' for x86-64 and 'arm64' for AArch64.
	// Windows uses 'windows-amd64', 'linux-amd64', 'darwin-amd64', etc.
	// Go download URLs: https://go.dev/dl/go1.21.0.linux-amd64.tar.gz
	downloadURL := fmt.Sprintf("https://go.dev/dl/go%s.%s-%s.tar.gz", version, osStr, archStr)

	if osStr == "windows" { // Go provides .zip for Windows
		downloadURL = fmt.Sprintf("https://go.dev/dl/go%s.%s-%s.zip", version, osStr, archStr)
	}

	if err := os.MkdirAll(installDir, 0755); err != nil {
		return fmt.Errorf("failed to create install directory %s: %w", installDir, err)
	}

	if err := downloadAndExtract(downloadURL, installDir); err != nil {
		return fmt.Errorf("failed to download and extract Go: %w", err)
	}

	// Go archives usually contain a top-level directory named "go"
	// We need to move its contents to the installDir directly.
	extractedGoDir := filepath.Join(installDir, "go")
	if _, err := os.Stat(extractedGoDir); err == nil {
		if err := util.MoveDirectoryContents(extractedGoDir, installDir); err != nil {
			return fmt.Errorf("failed to move extracted Go contents: %w", err)
		}
	} else if os.IsNotExist(err) {
		// This can happen if the archive itself extracts directly into installDir.
		// For example, if installDir was empty, and the archive expands `bin`, `src` etc directly.
		// This is okay, no action needed.
	} else {
		return fmt.Errorf("failed to stat extracted Go directory: %w", err)
	}


	// Create symlink for the 'go' binary in .devscope/bin
	goBinPath = filepath.Join(installDir, "bin", "go") // Recalculate path after move
	if err := util.CreateOrUpdateSymlink(goBinPath, filepath.Join(binLinkDir, "go")); err != nil {
		return fmt.Errorf("failed to link go binary: %w", err)
	}

	return g.CheckVersion(version, installDir)
}

func (g *GolangInstaller) CheckVersion(version string, installDir string) error {
	installedVersion, err := g.GetVersion(installDir)
	if err != nil {
		return err
	}
	if installedVersion != version {
		return fmt.Errorf("expected go %s, but found %s", version, installedVersion)
	}
	return nil
}

func (g *GolangInstaller) GetVersion(installDir string) (string, error) {
	goPath := filepath.Join(installDir, "bin", "go")
	if _, err := os.Stat(goPath); os.IsNotExist(err) {
		return "", fmt.Errorf("go binary not found in %s", installDir)
	}

	cmd := exec.Command(goPath, "version")
	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("failed to get go version: %w", err)
	}
	// Output is like "go version go1.21.0 darwin/amd64"
	parts := strings.Fields(string(output))
	if len(parts) < 3 {
		return "", fmt.Errorf("unexpected go version output: %s", string(output))
	}
	return strings.TrimPrefix(parts[2], "go"), nil
}
