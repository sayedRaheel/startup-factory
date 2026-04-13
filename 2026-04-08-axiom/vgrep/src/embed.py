import warnings
warnings.filterwarnings("ignore")
import os
# Suppress HuggingFace/Torch verbose symlink warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from sentence_transformers import SentenceTransformer
import numpy as np

class Embedder:
    def __init__(self):
        print("Loading on-device embedding model (all-MiniLM-L6-v2)...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def embed_text(self, text: str) -> np.ndarray:
        # Convert to raw numpy array natively
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.astype(np.float32)
