"""
Configuration for RAG POC.
"""

import atexit
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
LIBRARY_DIR = BASE_DIR.parent / "library" / "libraries"
QDRANT_PATH = BASE_DIR / "data" / "qdrant"
COLLECTION_NAME = "frameworks"

# Qdrant config - use Docker mode by default for better performance
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_MODE = os.getenv("QDRANT_MODE", "docker")  # "docker" or "local"

# Embedding config
USE_OLLAMA_EMBED = os.getenv("USE_OLLAMA_EMBED", "false").lower() == "true"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")

# Sentence-transformers model (used when Ollama embedding is disabled)
SBERT_MODEL = os.getenv("SBERT_MODEL", "all-MiniLM-L6-v2")

# Indexing config
BATCH_SIZE = 100  # Documents per batch for embedding
MAX_FRAMEWORKS = int(os.getenv("MAX_FRAMEWORKS", "0"))  # 0 = all

# Search config
TOP_K = 5  # Number of results to retrieve

# Singleton Qdrant client
_qdrant_client = None


def get_qdrant_client():
    """Get or create the singleton Qdrant client."""
    global _qdrant_client
    if _qdrant_client is None:
        from qdrant_client import QdrantClient

        if QDRANT_MODE == "local":
            QDRANT_PATH.mkdir(parents=True, exist_ok=True)
            _qdrant_client = QdrantClient(path=str(QDRANT_PATH))
        else:
            # Docker/server mode
            _qdrant_client = QdrantClient(url=QDRANT_URL)
    return _qdrant_client


def close_qdrant_client():
    """Close the Qdrant client."""
    global _qdrant_client
    if _qdrant_client is not None:
        try:
            _qdrant_client.close()
        except Exception:
            pass  # Ignore errors during shutdown
        _qdrant_client = None


# Register cleanup on exit
atexit.register(close_qdrant_client)
