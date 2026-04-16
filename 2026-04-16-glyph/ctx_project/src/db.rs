use rusqlite::{Connection, Result};
use directories::ProjectDirs;
use std::fs;
use std::path::PathBuf;

pub fn get_db_path() -> PathBuf {
    let proj_dirs = ProjectDirs::from("com", "ctx", "state").expect("No valid home directory");
    let dir = proj_dirs.config_dir();
    if !dir.exists() {
        let _ = fs::create_dir_all(dir);
    }
    dir.join("ctx.db")
}

pub fn init_db() -> Result<Connection> {
    let path = get_db_path();
    let conn = Connection::open(&path)?;
    
    // Architect constraint: Enable WAL so daemon writes don't block user reads.
    // Added: busy_timeout prevents SQLITE_BUSY errors when locks briefly collide.
    conn.execute_batch(
        "PRAGMA journal_mode = WAL;
         PRAGMA synchronous = NORMAL;
         PRAGMA busy_timeout = 5000;
         CREATE TABLE IF NOT EXISTS context_events (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             project_path TEXT NOT NULL,
             event_type TEXT NOT NULL,
             payload TEXT NOT NULL,
             timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
         );"
    )?;
    Ok(conn)
}

pub fn insert_event(conn: &Connection, project_path: &str, event_type: &str, payload: &str) -> Result<()> {
    conn.execute(
        "INSERT INTO context_events (project_path, event_type, payload) VALUES (?1, ?2, ?3)",
        (project_path, event_type, payload),
    )?;
    Ok(())
}
