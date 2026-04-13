use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize, Serialize)]
pub struct TetherConfig {
    pub strict_mode: bool,
}

impl Default for TetherConfig {
    fn default() -> Self {
        Self { strict_mode: true }
    }
}
