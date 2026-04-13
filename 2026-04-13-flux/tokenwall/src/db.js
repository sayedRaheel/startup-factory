const Database = require('better-sqlite3');
const path = require('path');

// Initialize database using relative path
const dbPath = path.join(__dirname, '..', 'tokenwall.db');
const db = new Database(dbPath);

// Enforce WAL mode for better concurrency and performance
db.pragma('journal_mode = WAL');

// Define exact schema requirements from ADR
db.exec(`
    CREATE TABLE IF NOT EXISTS usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        cost REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS file_cache (
        filepath TEXT PRIMARY KEY,
        hash TEXT NOT NULL,
        last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
    );
`);

module.exports = db;
