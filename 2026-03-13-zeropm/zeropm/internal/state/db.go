package state

import (
	"database/sql"
	"os"
	"path/filepath"
	_ "modernc.org/sqlite"
)

// InitDB ensures the .zeropm directory exists and opens the SQLite connection
func InitDB() (*sql.DB, error) {
	dir := ".zeropm"
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, err
	}

	dbPath := filepath.Join(dir, "state.db")
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, err
	}

	// Create tables if they don't exist
	schema := `
	CREATE TABLE IF NOT EXISTS tasks (
		id TEXT PRIMARY KEY,
		status TEXT NOT NULL,
		commit_hash TEXT
	);`
	if _, err := db.Exec(schema); err != nil {
		return nil, err
	}

	return db, nil
}
