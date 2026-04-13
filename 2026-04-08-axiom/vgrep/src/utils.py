def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list:
    # Word-level chunking
    words = text.split()
    chunks = []
    if not words:
        return chunks
    
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i+chunk_size])
        chunks.append(chunk)
        i += (chunk_size - overlap)
    return chunks
