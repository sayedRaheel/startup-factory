package tools

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/devscope/devscope/internal/project"
	"github.com/devscope/devscope/internal/ui"
	"github.com/devscope/devscope/internal/util"
)

// ToolInstaller defines the interface for installing and checking tool versions.
type ToolInstaller interface {
	Name() string
	Install(version string, installDir string, binLinkDir string) error
	CheckVersion(version string, installDir string) error // installDir is where the tool *should* be
	GetVersion(installDir string) (string, error)         // gets the actual installed version
}

// ToolManager orchestrates tool installations and version checks.
type ToolManager struct{}

func NewToolManager() *ToolManager {
	return &ToolManager{}
}

// CheckToolVersion checks if the required tool version is installed at the expected location.
func (tm *ToolManager) CheckToolVersion(installer ToolInstaller, requiredVersion string) error {
	projectRoot, err := project.GetProjectRoot()
	if err != nil {
		return fmt.Errorf("could not determine project root: %w", err)
	}
	toolsDir, err := project.GetDevScopeToolsDirPath()
	if err != nil {
		return fmt.Errorf("could not determine tools directory: %w", err)
	}
	installDir := filepath.Join(toolsDir, installer.Name(), requiredVersion)

	if _, err := os.Stat(installDir); os.IsNotExist(err) {
		return fmt.Errorf("%s %s is not installed in %s", installer.Name(), requiredVersion, installDir)
	}

	installedVersion, err := installer.GetVersion(installDir)
	if err != nil {
		return fmt.Errorf("failed to get installed %s version: %w", installer.Name(), err)
	}

	if installedVersion != requiredVersion {
		return fmt.Errorf("installed %s version mismatch: expected %s, got %s", installer.Name(), requiredVersion, installedVersion)
	}

	return nil
}

// downloadAndExtract downloads a file from URL and extracts it to targetDir.
func downloadAndExtract(url, targetDir string) error {
	ui.Info(fmt.Sprintf("Downloading from %s...", url))
	archivePath, err := util.DownloadFile(targetDir, url)
	if err != nil {
		return fmt.Errorf("failed to download: %w", err)
	}
	defer os.Remove(archivePath) // Clean up the downloaded archive

	ui.Info(fmt.Sprintf("Extracting %s to %s...", filepath.Base(archivePath), targetDir))
	if strings.HasSuffix(archivePath, ".zip") {
		return util.Unzip(archivePath, targetDir)
	} else if strings.HasSuffix(archivePath, ".tar.gz") || strings.HasSuffix(archivePath, ".tgz") {
		return util.UntarGz(archivePath, targetDir)
	}
	return fmt.Errorf("unsupported archive type for %s", archivePath)
}
