package util

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/devscope/devscope/internal/ui"
)

// DownloadFile downloads a file from a given URL to a specified directory.
// It returns the path to the downloaded file.
func DownloadFile(destDir, url string) (string, error) {
	// Get the filename from the URL
	tokens := strings.Split(url, "/")
	filename := tokens[len(tokens)-1]
	if filename == "" || strings.Contains(filename, "?") { // Basic check for invalid filenames or query strings
		return "", fmt.Errorf("could not determine filename from URL: %s", url)
	}

	filePath := filepath.Join(destDir, filename)

	// Create the destination directory if it doesn't exist
	if err := os.MkdirAll(destDir, 0755); err != nil {
		return "", fmt.Errorf("failed to create destination directory %s: %w", destDir, err)
	}

	// Create the file
	out, err := os.Create(filePath)
	if err != nil {
		return "", fmt.Errorf("failed to create file %s: %w", filePath, err)
	}
	defer out.Close()

	// Get the data
	resp, err := http.Get(url)
	if err != nil {
		return "", fmt.Errorf("failed to download from %s: %w", url, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("bad status code for %s: %s", url, resp.Status)
	}

	// Write the body to file
	progressReader := &progressReader{
		Reader: resp.Body,
		total:  resp.ContentLength,
		name:   filename,
	}

	_, err = io.Copy(out, progressReader)
	if err != nil {
		return "", fmt.Errorf("failed to write downloaded file: %w", err)
	}

	ui.Info(fmt.Sprintf("Downloaded %s to %s", filename, filePath))
	return filePath, nil
}

// DownloadFileDirect downloads a single binary file to destDir with a specific filename.
func DownloadFileDirect(destDir, url, filename string) (string, error) {
	filePath := filepath.Join(destDir, filename)

	if err := os.MkdirAll(destDir, 0755); err != nil {
		return "", fmt.Errorf("failed to create destination directory %s: %w", destDir, err)
	}

	out, err := os.Create(filePath)
	if err != nil {
		return "", fmt.Errorf("failed to create file %s: %w", filePath, err)
	}
	defer out.Close()

	resp, err := http.Get(url)
	if err != nil {
		return "", fmt.Errorf("failed to download from %s: %w", url, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("bad status code for %s: %s", url, resp.Status)
	}

	progressReader := &progressReader{
		Reader: resp.Body,
		total:  resp.ContentLength,
		name:   filename,
	}

	_, err = io.Copy(out, progressReader)
	if err != nil {
		return "", fmt.Errorf("failed to write downloaded file: %w", err)
	}

	ui.Info(fmt.Sprintf("Downloaded %s to %s", filename, filePath))
	return filePath, nil
}

// progressReader wraps an io.Reader to provide progress updates.
type progressReader struct {
	io.Reader
	total   int64 // Total bytes expected
	current int64 // Bytes read so far
	name    string
	lastP   int   // Last reported percentage
}

func (pr *progressReader) Read(p []byte) (n int, err error) {
	n, err = pr.Reader.Read(p)
	pr.current += int64(n)

	if pr.total > 0 {
		percentage := int(float64(pr.current) / float64(pr.total) * 100)
		if percentage%10 == 0 && percentage != pr.lastP { // Update every 10%
			ui.Info(fmt.Sprintf("Downloading %s: %d%% (%d/%d bytes)", pr.name, percentage, pr.current, pr.total))
			pr.lastP = percentage
		}
	} else if pr.current > 0 {
		// If total is unknown, just show bytes
		// For simplicity, we'll only show progress if total is known.
	}
	return
}
