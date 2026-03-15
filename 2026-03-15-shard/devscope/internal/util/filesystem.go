package util

import (
	"archive/tar"
	"archive/zip"
	"compress/gzip"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

// Unzip extracts a zip archive to the specified destination.
func Unzip(src, dest string) error {
	r, err := zip.OpenReader(src)
	if err != nil {
		return fmt.Errorf("failed to open zip file: %w", err)
	}
	defer r.Close()

	for _, f := range r.File {
		fpath := filepath.Join(dest, f.Name)

		if !strings.HasPrefix(fpath, filepath.Clean(dest)+string(os.PathSeparator)) {
			return fmt.Errorf("illegal file path: %s", fpath)
		}

		if f.FileInfo().IsDir() {
			os.MkdirAll(fpath, os.ModePerm)
			continue
		}

		if err = os.MkdirAll(filepath.Dir(fpath), os.ModePerm); err != nil {
			return err
		}

		outFile, err := os.OpenFile(fpath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.Mode())
		if err != nil {
			return err
		}

		rc, err := f.Open()
		if err != nil {
			return err
		}

		_, err = io.Copy(outFile, rc)

		outFile.Close()
		rc.Close()

		if err != nil {
			return err
		}
	}
	return nil
}

// UntarGz extracts a .tar.gz archive to the specified destination.
func UntarGz(src, dest string) error {
	file, err := os.Open(src)
	if err != nil {
		return fmt.Errorf("failed to open tar.gz file: %w", err)
	}
	defer file.Close()

	gzr, err := gzip.NewReader(file)
	if err != nil {
		return fmt.Errorf("failed to create gzip reader: %w", err)
	}
	defer gzr.Close()

	tr := tar.NewReader(gzr)

	for {
		header, err := tr.Next()
		if err == io.EOF {
			break // End of archive
		}
		if err != nil {
			return fmt.Errorf("failed to read tar header: %w", err)
		}

		target := filepath.Join(dest, header.Name)

		// Check for directory traversal
		if !strings.HasPrefix(target, filepath.Clean(dest)+string(os.PathSeparator)) {
			return fmt.Errorf("illegal file path: %s", target)
		}

		switch header.Typeflag {
		case tar.DIR:
			if err := os.MkdirAll(target, os.FileMode(header.Mode)); err != nil {
				return fmt.Errorf("failed to create directory %s: %w", target, err)
			}
		case tar.REGTYPE:
			if err := os.MkdirAll(filepath.Dir(target), os.FileMode(header.Mode)); err != nil {
				return fmt.Errorf("failed to create parent directory for %s: %w", target, err)
			}
			f, err := os.OpenFile(target, os.O_CREATE|os.O_RDWR, os.FileMode(header.Mode))
			if err != nil {
				return fmt.Errorf("failed to create file %s: %w", target, err)
			}
			if _, err := io.Copy(f, tr); err != nil {
				f.Close()
				return fmt.Errorf("failed to write file %s: %w", target, err)
			}
			f.Close()
		case tar.SYMLINK:
			// Handle symlinks
			if err := os.Symlink(header.Linkname, target); err != nil {
				return fmt.Errorf("failed to create symlink %s -> %s: %w", target, header.Linkname, err)
			}
		default:
			// Ignore other types for a simple extractor (e.g., hard links, devices)
		}
	}
	return nil
}

// CreateOrUpdateSymlink creates a symlink from oldname to newname. If newname already exists and is a symlink,
// it updates it. If it's a regular file/dir, it returns an error.
func CreateOrUpdateSymlink(oldname, newname string) error {
	// Ensure the directory for the symlink exists
	if err := os.MkdirAll(filepath.Dir(newname), 0755); err != nil {
		return fmt.Errorf("failed to create directory for symlink %s: %w", newname, err)
	}

	// Check if the symlink already exists
	if fi, err := os.Lstat(newname); err == nil {
		if fi.Mode()&os.ModeSymlink != 0 {
			// It's a symlink, check if it points to the correct location
			currentLinkTarget, err := os.Readlink(newname)
			if err != nil {
				return fmt.Errorf("failed to read existing symlink %s: %w", newname, err)
			}
			if currentLinkTarget == oldname {
				// Symlink is already correct, no need to update
				return nil
			}
			// Remove existing symlink to create a new one
			if err := os.Remove(newname); err != nil {
				return fmt.Errorf("failed to remove existing symlink %s: %w", newname, err)
			}
		} else {
			return fmt.Errorf("target path %s exists but is not a symlink; refusing to overwrite", newname)
		}
	} else if !os.IsNotExist(err) {
		return fmt.Errorf("failed to stat %s: %w", newname, err)
	}

	// Create the new symlink
	return os.Symlink(oldname, newname)
}

// MoveDirectoryContents moves all files and directories from src to dest.
// src directory will be removed after successful move.
func MoveDirectoryContents(src, dest string) error {
	entries, err := os.ReadDir(src)
	if err != nil {
		return fmt.Errorf("failed to read source directory %s: %w", src, err)
	}

	for _, entry := range entries {
		srcPath := filepath.Join(src, entry.Name())
		destPath := filepath.Join(dest, entry.Name())

		// Attempt to rename/move directly
		if err := os.Rename(srcPath, destPath); err != nil {
			// If rename fails, try copying (e.g., cross-device link)
			if !os.IsExist(err) { // If it's not "file exists", then it's a real rename error
				return fmt.Errorf("failed to rename %s to %s: %w", srcPath, destPath, err)
			}
			// If destPath exists, and it's a directory, we need to merge
			if entry.IsDir() {
				if err := os.MkdirAll(destPath, 0755); err != nil {
					return fmt.Errorf("failed to create destination directory for merge %s: %w", destPath, err)
				}
				if err := MoveDirectoryContents(srcPath, destPath); err != nil { // Recurse for directories
					return err
				}
			} else {
				return fmt.Errorf("failed to rename %s to %s: target exists %w", srcPath, destPath, err)
			}
		}
	}

	// Remove the source directory after moving its contents
	return os.RemoveAll(src)
}

// ErrorsToStrings converts a slice of errors to a slice of their string representations.
func ErrorsToStrings(errs []error) []string {
	var s []string
	for _, err := range errs {
		s = append(s, err.Error())
	}
	return s
}
