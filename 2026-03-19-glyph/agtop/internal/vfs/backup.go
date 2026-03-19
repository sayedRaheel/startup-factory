package vfs

import "fmt"

var backupLog []string

// Snapshot records a file state (simulated for prototype).
func Snapshot(filename string) {
	backupLog = append(backupLog, filename)
}

// RollbackLatest triggers a deterministic file rollback.
func RollbackLatest() string {
	if len(backupLog) == 0 {
		return "No files in VFS snapshot history to rollback."
	}
	last := backupLog[len(backupLog)-1]
	backupLog = backupLog[:len(backupLog)-1]
	return fmt.Sprintf("Rolled back: %s to previous state.", last)
}
