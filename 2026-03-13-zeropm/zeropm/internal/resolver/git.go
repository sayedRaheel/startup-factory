package resolver

import (
	"fmt"
	"os/exec"
)

// CommitTask auto-commits the state of a completed task to git
func CommitTask(taskID string) error {
	cmd := exec.Command("git", "commit", "-am", fmt.Sprintf("chore(zeropm): auto-resolve task %s", taskID))
	return cmd.Run()
}
