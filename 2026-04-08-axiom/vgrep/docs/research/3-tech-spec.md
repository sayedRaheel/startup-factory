### Tech Spec
- **Original Architecture:** Rust (Rusqlite + Candle). 
- **Adapted Architecture:** Python (SQLite built-in + SentenceTransformers/NumPy).
- **Embedding Model:** `all-MiniLM-L6-v2` (384-dimensions, locally cached).
- **Storage Strategy:** Chunk text, generate embeddings, store directly as BLOB in `.vgrep/index.db`.
