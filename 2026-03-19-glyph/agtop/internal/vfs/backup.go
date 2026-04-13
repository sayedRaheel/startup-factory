package vfs

import (
	"fmt"
	"os"
	"path/filepath"
)

type snapshot struct {
	filename    string
	content     []byte
	existed     bool
	permissions os.FileMode
}

var backupLog []snapshot

// Snapshot records a file state in memory right before an overwrite.
func Snapshot(filename string) {
	s := snapshot{filename: filename}
	info, err := os.Stat(filename)
	if err == nil {
		s.existed = true
		s.permissions = info.Mode()
		b, _ := os.ReadFile(filename)
		s.content = b
	} else {
		s.existed = false
	}
	backupLog = append(backupLog, s)
}

// RollbackLatest triggers a deterministic file rollback.
func RollbackLatest() string {
	if len(backupLog) == 0 {
		return "No files in VFS snapshot history to rollback."
	}
	last := backupLog[len(backupLog)-1]
	backupLog = backupLog[:len(backupLog)-1]

	if !last.existed {
		os.Remove(last.filename)
		return fmt.Sprintf("Rolled back: Deleted %s (did not exist previously).", last.filename)
	}

	// Restore previous content
	os.MkdirAll(filepath.Dir(last.filename), 0755)
	os.WriteFile(last.filename, last.content, last.permissions)
	return fmt.Sprintf("Rolled back: Restored %s to previous state.", last.filename)
}
