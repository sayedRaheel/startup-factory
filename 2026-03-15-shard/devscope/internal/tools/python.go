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

// PythonInstaller implements ToolInstaller for Python
type PythonInstaller struct{}

func NewPythonInstaller() *PythonInstaller {
	return &PythonInstaller{}
}

func (p *PythonInstaller) Name() string {
	return "python"
}

func (p *PythonInstaller) Install(version string, installDir string, binLinkDir string) error {
	// Check if Python is already installed at the target location
	pythonBinPath := filepath.Join(installDir, "bin", "python")
	if _, err := os.Stat(pythonBinPath); err == nil {
		if err := p.CheckVersion(version, installDir); err == nil {
			return nil // Correct version already installed
		}
		ui.Info(fmt.Sprintf("Python %s found, but not version %s. Reinstalling...", p.GetVersion(installDir), version))
		os.RemoveAll(installDir) // Clean up old installation
	}

	osStr := runtime.GOOS
	archStr := runtime.GOARCH

	// Adjust arch for specific Python distributions if necessary
	if archStr == "amd64" {
		archStr = "x86_64" // Common for Python binary builds
	} else if archStr == "arm64" && osStr == "darwin" {
		archStr = "arm64"
	} else if archStr == "arm64" && osStr == "linux" {
		archStr = "aarch64" // Common for Linux ARM64
	}

	// IMPORTANT: This URL is a placeholder for a hypothetical pre-built Python distribution.
	// In a real application, you would need a robust mechanism to find
	// and download portable Python distributions for various OS/arch combinations.
	// For this prototype, we assume such a direct tarball is available and follows a consistent structure.
	downloadURL := fmt.Sprintf("https://cdn.devscope.tools/python-v%s-%s-%s.tar.gz", version, osStr, archStr) // Placeholder URL

	if err := os.MkdirAll(installDir, 0755); err != nil {
		return fmt.Errorf("failed to create install directory %s: %w", installDir, err)
	}

	if err := downloadAndExtract(downloadURL, installDir); err != nil {
		// Provide a more user-friendly error for the placeholder nature
		return fmt.Errorf("failed to download and extract Python from %s (NOTE: This is a placeholder URL for prototype demonstration. Actual Python distribution URLs vary by platform and may require a more complex lookup or different installation strategy): %w", downloadURL, err)
	}

	// Python archives often extract into a top-level directory like "python-v3.10.0-linux-amd64"
	// or "Python-3.10.0" or directly into the target if it's a minimal build.
	// We need to check for this and move contents if necessary.
	// Hypothetical extracted dir name based on downloadURL
	extractedDirName := fmt.Sprintf("python-v%s-%s-%s", version, osStr, archStr)
	possibleExtractedPath := filepath.Join(installDir, extractedDirName)

	if _, err := os.Stat(possibleExtractedPath); err == nil {
		if err := util.MoveDirectoryContents(possibleExtractedPath, installDir); err != nil {
			return fmt.Errorf("failed to move extracted Python contents: %w", err)
		}
	} else if !os.IsNotExist(err) {
		return fmt.Errorf("failed to stat potential extracted Python directory %s: %w", possibleExtractedPath, err)
	}

	// After potential move, check for the 'bin' directory and python executable
	pythonBinPath = filepath.Join(installDir, "bin", "python")
	if _, err := os.Stat(pythonBinPath); os.IsNotExist(err) {
		return fmt.Errorf("could not find python binary at %s after installation", pythonBinPath)
	}

	// Create symlinks in .devscope/bin
	if err := util.CreateOrUpdateSymlink(pythonBinPath, filepath.Join(binLinkDir, "python")); err != nil {
		return fmt.Errorf("failed to link python: %w", err)
	}
	// Also symlink pip if it's found
	pipBinPath := filepath.Join(installDir, "bin", "pip")
	if _, err := os.Stat(pipBinPath); err == nil { // Only link if pip exists
		if err := util.CreateOrUpdateSymlink(pipBinPath, filepath.Join(binLinkDir, "pip")); err != nil {
			return fmt.Errorf("failed to link pip: %w", err)
		}
	} else if !os.IsNotExist(err) {
		return fmt.Errorf("failed to stat pip binary at %s: %w", pipBinPath, err)
	}


	return p.CheckVersion(version, installDir)
}

func (p *PythonInstaller) CheckVersion(version string, installDir string) error {
	installedVersion, err := p.GetVersion(installDir)
	if err != nil {
		return err
	}
	if installedVersion != version {
		return fmt.Errorf("expected python %s, but found %s", version, installedVersion)
	}
	return nil
}

func (p *PythonInstaller) GetVersion(installDir string) (string, error) {
	pythonPath := filepath.Join(installDir, "bin", "python")
	if _, err := os.Stat(pythonPath); os.IsNotExist(err) {
		return "", fmt.Errorf("python binary not found in %s", installDir)
	}

	cmd := exec.Command(pythonPath, "--version")
	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("failed to get python version: %w", err)
	}
	// Output is like "Python 3.10.0"
	parts := strings.Fields(strings.TrimSpace(string(output)))
	if len(parts) < 2 {
		return "", fmt.Errorf("unexpected python version output: %s", string(output))
	}
	return parts[1], nil // Should be "3.10.0"
}
