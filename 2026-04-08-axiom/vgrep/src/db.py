import sqlite3
import os

def init_db():
    os.makedirs(".vgrep", exist_ok=True)
    conn = sqlite3.connect(".vgrep/index.db")
    conn.execute('''
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY,
            file_path TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding BLOB NOT NULL
        )
    ''')
    # Clear existing data to allow re-indexing safely
    conn.execute('DELETE FROM chunks')
    conn.commit()
    return conn

def insert_chunk(conn, file_path, content, embedding_bytes):
    conn.execute('''
        INSERT INTO chunks (file_path, content, embedding)
        VALUES (?, ?, ?)
    ''', (file_path, content, embedding_bytes))
    conn.commit()
