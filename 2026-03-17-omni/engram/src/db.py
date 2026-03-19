import sqlite3
import os

class DB:
    def __init__(self, db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        # WAL mode crucial for concurrent read/write
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self.conn.execute("PRAGMA synchronous = NORMAL;")
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS file_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                content_hash TEXT,
                compressed_content TEXT
            );
            
            CREATE TABLE IF NOT EXISTS session_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL
            );
        """)
        self.conn.commit()

    def log_event(self, path, event_type, hash_val, compressed):
        self.conn.execute(
            "INSERT INTO file_events (file_path, event_type, content_hash, compressed_content) VALUES (?, ?, ?, ?)",
            (path, event_type, hash_val, compressed)
        )
        self.conn.commit()

    def get_all_events(self):
        cur = self.conn.execute("SELECT * FROM file_events ORDER BY timestamp ASC")
        return cur.fetchall()
