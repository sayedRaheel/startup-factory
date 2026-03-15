package tools

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"strings"

	"github.com/devscope/devscope/internal/ui"
	"github.com/devscope/devscope/internal/util"
)

// CLIToolInstaller implements ToolInstaller for generic CLI tools
type CLIToolInstaller struct {
	toolName    string
	downloadURL string // URL template, e.g., "https://dl.k8s.io/release/v{version}/bin/linux/amd64/kubectl"
	binaryName  string // Expected binary name after extraction, e.g., "kubectl"
}

func NewCLIToolInstaller(name, url, binary string) *CLIToolInstaller {
	// If binary name isn't explicitly provided, infer from tool name
	if binary == "" {
		binary = name
	}
	return &CLIToolInstaller{
		toolName:    name,
		downloadURL: url,
		binaryName:  binary,
	}
}

func (c *CLIToolInstaller) Name() string {
	return c.toolName
}

func (c *CLIToolInstaller) Install(version string, installDir string, binLinkDir string) error {
	// Construct the final download URL from template
	finalURL := strings.ReplaceAll(c.downloadURL, "{version}", version)
	finalURL = strings.ReplaceAll(finalURL, "{os}", runtime.GOOS)
	finalURL = strings.ReplaceAll(finalURL, "{arch}", runtime.GOARCH) // e.g., amd64, arm64

	// Check if tool is already installed at the target location
	toolBinPath := filepath.Join(installDir, c.binaryName)
	if _, err := os.Stat(toolBinPath); err == nil {
		if err := c.CheckVersion(version, installDir); err == nil {
			return nil // Correct version already installed
		}
		ui.Info(fmt.Sprintf("%s %s found, but not version %s. Reinstalling...", c.toolName, c.GetVersion(installDir), version))
		os.RemoveAll(installDir) // Clean up old installation
	}

	if err := os.MkdirAll(installDir, 0755); err != nil {
		return fmt.Errorf("failed to create install directory %s: %w", installDir, err)
	}

	// Attempt download and extract (for archives)
	err := downloadAndExtract(finalURL, installDir)
	if err != nil {
		// If downloadAndExtract fails, it might be a direct binary download
		// rather than an archive. Try direct download.
		if strings.Contains(err.Error(), "unsupported archive type") || strings.Contains(err.Error(), "bad status code") {
			ui.Info(fmt.Sprintf("Attempting direct binary download for %s from %s...", c.toolName, finalURL))
			if err := util.DownloadFileDirect(installDir, finalURL, c.binaryName); err != nil {
				return fmt.Errorf("failed to download direct binary for %s: %w", c.toolName, err)
			}
			// Ensure it's executable
			if err := os.Chmod(toolBinPath, 0755); err != nil {
				return fmt.Errorf("failed to make %s executable: %w", toolBinPath, err)
			}
		} else {
			return fmt.Errorf("failed to download or extract %s: %w", c.toolName, err)
		}
	}

	// After extraction, the binary might be in a subdirectory (e.g., `helm-v3.12.0-linux-amd64/helm`).
	// If `installDir/binaryName` doesn't exist, try to find it.
	if _, err := os.Stat(toolBinPath); os.IsNotExist(err) {
		// Scan for the binary within the extracted contents (common for archives with root folders)
		searchPattern := filepath.Join(installDir, "**", c.binaryName)
		matches, globErr := filepath.Glob(searchPattern)
		if globErr == nil && len(matches) > 0 {
			// Take the first match and move it to the expected toolBinPath
			foundPath := matches[0]
			ui.Info(fmt.Sprintf("Found %s at %s, moving to %s", c.binaryName, foundPath, toolBinPath))
			if err := os.Rename(foundPath, toolBinPath); err != nil {
				return fmt.Errorf("failed to move %s from %s to %s: %w", c.binaryName, foundPath, toolBinPath, err)
			}
			// Best effort cleanup of the original extracted directory if it's now empty
			// Find the top-level directory where the binary was found
			relative := strings.TrimPrefix(foundPath, installDir+string(os.PathSeparator))
			if idx := strings.Index(relative, string(os.PathSeparator)); idx != -1 {
				extractedTopDir := filepath.Join(installDir, relative[:idx])
				_ = os.RemoveAll(extractedTopDir) // Ignore error, best effort
			}
		} else {
			return fmt.Errorf("expected binary %s not found after installation in %s or its subdirectories", c.binaryName, installDir)
		}
	}

	// Ensure the binary exists and is executable
	if _, err := os.Stat(toolBinPath); os.IsNotExist(err) {
		return fmt.Errorf("expected binary %s not found after installation in %s", c.binaryName, installDir)
	}
	if err := os.Chmod(toolBinPath, 0755); err != nil {
		return fmt.Errorf("failed to make %s executable: %w", toolBinPath, err)
	}

	// Create symlink in .devscope/bin
	if err := util.CreateOrUpdateSymlink(toolBinPath, filepath.Join(binLinkDir, c.binaryName)); err != nil {
		return fmt.Errorf("failed to link %s: %w", c.toolName, err)
	}

	return c.CheckVersion(version, installDir)
}

func (c *CLIToolInstaller) CheckVersion(version string, installDir string) error {
	installedVersion, err := c.GetVersion(installDir)
	if err != nil {
		return err
	}
	// Many tools prefix version with 'v', but devscope.yaml might not. Normalize.
	cleanedInstalledVersion := strings.TrimPrefix(installedVersion, "v")
	cleanedRequiredVersion := strings.TrimPrefix(version, "v")

	if cleanedInstalledVersion != cleanedRequiredVersion {
		return fmt.Errorf("expected %s %s, but found %s", c.toolName, version, installedVersion)
	}
	return nil
}

var versionRegex = regexp.MustCompile(`(v?\d+\.\d+\.\d+(?:-\w+(?:\.\d+)?)?)`)

func (c *CLIToolInstaller) GetVersion(installDir string) (string, error) {
	toolPath := filepath.Join(installDir, c.binaryName)
	if _, err := os.Stat(toolPath); os.IsNotExist(err) {
		return "", fmt.Errorf("%s binary not found in %s", c.toolName, installDir)
	}

	var cmd *exec.Cmd
	switch c.toolName {
	case "kubectl":
		// kubectl version --client -o=json is more robust, but parsing JSON is heavy for CLI.
		// Fallback to simpler string parsing.
		cmd = exec.Command(toolPath, "version", "--client")
	case "helm":
		cmd = exec.Command(toolPath, "version", "--template", "{{.Version}}")
	default:
		// Most CLI tools support `--version` or `version` subcommand
		cmd = exec.Command(toolPath, "version")
	}

	output, err := cmd.CombinedOutput()
	if err != nil {
		// Some tools output to stdout even on error exit code, or use stderr.
		// Check output even if command returns an error.
		errorOutput := strings.TrimSpace(string(output))
		if !strings.Contains(errorOutput, "version") && !strings.Contains(errorOutput, c.toolName) {
			return "", fmt.Errorf("failed to get %s version: %w, output: %s", c.toolName, err, errorOutput)
		}
	}

	versionOutput := strings.TrimSpace(string(output))

	// Attempt to extract version number using a regex
	matches := versionRegex.FindStringSubmatch(versionOutput)
	if len(matches) > 1 {
		return matches[1], nil
	}

	return "", fmt.Errorf("could not parse %s version from output: %s", c.toolName, versionOutput)
}
