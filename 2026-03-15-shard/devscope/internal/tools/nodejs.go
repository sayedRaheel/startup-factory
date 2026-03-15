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

// NodeJSInstaller implements ToolInstaller for Node.js
type NodeJSInstaller struct{}

func NewNodeJSInstaller() *NodeJSInstaller {
	return &NodeJSInstaller{}
}

func (n *NodeJSInstaller) Name() string {
	return "node"
}

func (n *NodeJSInstaller) Install(version string, installDir string, binLinkDir string) error {
	// Check if Node.js is already installed at the target location
	nodeBinPath := filepath.Join(installDir, "bin", "node")
	if _, err := os.Stat(nodeBinPath); err == nil {
		if err := n.CheckVersion(version, installDir); err == nil {
			return nil // Correct version already installed
		}
		ui.Info(fmt.Sprintf("Node.js %s found, but not version %s. Reinstalling...", n.GetVersion(installDir), version))
		os.RemoveAll(installDir) // Clean up old installation
	}

	osStr := runtime.GOOS
	archStr := runtime.GOARCH

	// Determine correct architecture string for Node.js downloads
	if archStr == "amd64" {
		archStr = "x64"
	} else if archStr == "arm64" && osStr == "darwin" {
		archStr = "arm64"
	} else if archStr == "arm64" && osStr == "linux" {
		archStr = "arm64" // Node.js often uses aarch64 for Linux ARM64
	}

	// Example URL format: https://nodejs.org/dist/v18.17.0/node-v18.17.0-darwin-x64.tar.gz
	downloadURL := fmt.Sprintf("https://nodejs.org/dist/v%s/node-v%s-%s-%s.tar.gz", version, version, osStr, archStr)

	if err := os.MkdirAll(installDir, 0755); err != nil {
		return fmt.Errorf("failed to create install directory %s: %w", installDir, err)
	}

	if err := downloadAndExtract(downloadURL, installDir); err != nil {
		return fmt.Errorf("failed to download and extract Node.js: %w", err)
	}

	// Node.js archives usually contain a top-level directory (e.g., node-v18.17.0-darwin-x64)
	// We need to move its contents to the installDir directly.
	extractedDir := filepath.Join(installDir, fmt.Sprintf("node-v%s-%s-%s", version, osStr, archStr))
	if _, err := os.Stat(extractedDir); err == nil {
		if err := util.MoveDirectoryContents(extractedDir, installDir); err != nil {
			return fmt.Errorf("failed to move extracted Node.js contents: %w", err)
		}
	}


	// Create symlinks in .devscope/bin
	nodeBinPath = filepath.Join(installDir, "bin", "node") // Recalculate after move
	npmBinPath := filepath.Join(installDir, "bin", "npm")
	npxBinPath := filepath.Join(installDir, "bin", "npx")

	if err := util.CreateOrUpdateSymlink(nodeBinPath, filepath.Join(binLinkDir, "node")); err != nil {
		return fmt.Errorf("failed to link node: %w", err)
	}
	if err := util.CreateOrUpdateSymlink(npmBinPath, filepath.Join(binLinkDir, "npm")); err != nil {
		return fmt.Errorf("failed to link npm: %w", err)
	}
	if err := util.CreateOrUpdateSymlink(npxBinPath, filepath.Join(binLinkDir, "npx")); err != nil {
		return fmt.Errorf("failed to link npx: %w", err)
	}


	return n.CheckVersion(version, installDir)
}

func (n *NodeJSInstaller) CheckVersion(version string, installDir string) error {
	installedVersion, err := n.GetVersion(installDir)
	if err != nil {
		return err
	}
	if installedVersion != version {
		return fmt.Errorf("expected node %s, but found %s", version, installedVersion)
	}
	return nil
}

func (n *NodeJSInstaller) GetVersion(installDir string) (string, error) {
	nodePath := filepath.Join(installDir, "bin", "node")
	if _, err := os.Stat(nodePath); os.IsNotExist(err) {
		return "", fmt.Errorf("node not found in %s", installDir)
	}

	cmd := exec.Command(nodePath, "--version")
	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("failed to get node version: %w", err)
	}
	return strings.TrimSpace(strings.TrimPrefix(string(output), "v")), nil
}
