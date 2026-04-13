use git2::{Repository, WorktreeAddOptions};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};
use std::fs;
use std::process::Command;

pub struct Sandbox {
    workspace_root: PathBuf,
    pub sandbox_path: PathBuf,
    branch_name: String,
}

impl Sandbox {
    pub fn init(workspace_root: &Path) -> Result<Self, Box<dyn std::error::Error>> {
        let repo = Repository::open(workspace_root).map_err(|_| "Not a git repository. Warden requires a git repository to manage worktrees")?;

        let timestamp = SystemTime::now().duration_since(UNIX_EPOCH)?.as_nanos();
        let branch_name = format!("warden-sandbox-{}", timestamp);
        let sandbox_path = workspace_root.join(".warden").join("sandbox");

        let _ = fs::remove_dir_all(&sandbox_path);

        println!("Creating ephemeral git worktree at {:?}", sandbox_path);

        // Branching using git2
        let head = repo.head()?;
        let commit = head.peel_to_commit()?;
        repo.branch(&branch_name, &commit, false)?;

        // Creating worktree using git2
        let mut opts = WorktreeAddOptions::new();
        let mut reference = repo.find_reference(&format!("refs/heads/{}", branch_name))?;
        opts.reference(Some(&mut reference));
        repo.worktree(&branch_name, &sandbox_path, Some(&mut opts))?;

        Ok(Sandbox {
            workspace_root: workspace_root.to_path_buf(),
            sandbox_path,
            branch_name,
        })
    }

    pub fn merge_to_main(&self) -> Result<(), Box<dyn std::error::Error>> {
        println!("Tests passed. Merging {} into main workspace...", self.branch_name);

        // Adding and committing changes
        let status = Command::new("git")
            .arg("add")
            .arg(".")
            .current_dir(&self.sandbox_path)
            .status()?;
        if !status.success() {
            return Err("Failed to add files in sandbox".into());
        }

        let output = Command::new("git")
            .arg("status")
            .arg("--porcelain")
            .current_dir(&self.sandbox_path)
            .output()?;

        if !output.stdout.is_empty() {
            let commit_status = Command::new("git")
                .args(["commit", "-m", "Warden automated commit"])
                .current_dir(&self.sandbox_path)
                .status()?;
            if !commit_status.success() {
                return Err("Failed to commit in sandbox".into());
            }
        }

        // Fast-forward merge using command since doing it via git2 requires many boilerplate steps
        let merge_status = Command::new("git")
            .args(["merge", "--ff-only", &self.branch_name])
            .current_dir(&self.workspace_root)
            .status()?;

        if !merge_status.success() {
            return Err("Merge failed".into());
        }

        Ok(())
    }

    pub fn cleanup(&self) {
        println!("Destroying ephemeral sandbox...");
        let _ = Command::new("git")
            .args(["worktree", "remove", "-f"])
            .arg(&self.sandbox_path)
            .current_dir(&self.workspace_root)
            .output();

        let _ = Command::new("git")
            .args(["branch", "-D", &self.branch_name])
            .current_dir(&self.workspace_root)
            .output();

        let _ = fs::remove_dir_all(&self.sandbox_path);
    }
}

impl Drop for Sandbox {
    fn drop(&mut self) {
        self.cleanup();
    }
}
