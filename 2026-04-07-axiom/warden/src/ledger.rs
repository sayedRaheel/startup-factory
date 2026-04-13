use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Serialize, Deserialize, Debug)]
pub struct Attempt {
    pub iteration: i32,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error_trace: Option<String>,
    pub success: bool,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Ledger {
    #[serde(default)]
    pub task: String,
    pub attempts: Vec<Attempt>,
}

pub struct Manager {
    filepath: PathBuf,
}

impl Manager {
    pub fn new(workspace_root: &Path) -> Self {
        let warden_dir = workspace_root.join(".warden");
        fs::create_dir_all(&warden_dir).expect("Failed to create .warden directory");
        Manager {
            filepath: warden_dir.join("ledger.json"),
        }
    }

    pub fn load(&self) -> Result<Ledger, Box<dyn std::error::Error>> {
        if !self.filepath.exists() {
            return Ok(Ledger {
                task: String::new(),
                attempts: Vec::new(),
            });
        }
        let data = fs::read_to_string(&self.filepath)?;
        let ledger: Ledger = serde_json::from_str(&data)?;
        Ok(ledger)
    }

    pub fn save(&self, ledger: &Ledger) -> Result<(), Box<dyn std::error::Error>> {
        let data = serde_json::to_string_pretty(ledger)?;
        fs::write(&self.filepath, data)?;
        Ok(())
    }
}
