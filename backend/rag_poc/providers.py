"""
Provider implementations for embeddings and LLM.
Demonstrates the abstraction pattern - swap implementations without changing consumer code.
"""

from typing import Protocol, Iterator
import json

import config


class Embedder(Protocol):
    """Interface for embedding providers."""

    @property
    def dimensions(self) -> int:
        """Return embedding dimensions."""
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query."""
        ...


class LLM(Protocol):
    """Interface for LLM providers."""

    def generate(self, prompt: str, context: str) -> str:
        """Generate a response."""
        ...

    def stream(self, prompt: str, context: str) -> Iterator[str]:
        """Stream response tokens."""
        ...


# ============================================================================
# Sentence-Transformers Embedder (default, no external service needed)
# ============================================================================


class SentenceTransformerEmbedder:
    """Local embeddings using sentence-transformers."""

    def __init__(self, model_name: str = config.SBERT_MODEL):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        self._dimensions = self.model.get_sentence_embedding_dimension()

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


# ============================================================================
# Ollama Embedder (requires Ollama server)
# ============================================================================


class OllamaEmbedder:
    """Embeddings using Ollama server."""

    def __init__(
        self,
        model: str = config.OLLAMA_EMBED_MODEL,
        base_url: str = config.OLLAMA_BASE_URL,
    ):
        import httpx

        self.model = model
        self.base_url = base_url
        self.client = httpx.Client(timeout=60)
        self._dimensions: int | None = None

    @property
    def dimensions(self) -> int:
        if self._dimensions is None:
            test = self.embed_query("test")
            self._dimensions = len(test)
        return self._dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        for text in texts:
            embeddings.append(self.embed_query(text))
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        resp = self.client.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.model, "prompt": text},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]


# ============================================================================
# Ollama LLM
# ============================================================================


class OllamaLLM:
    """LLM using Ollama server."""

    SYSTEM_PROMPT = """You are a GRC (Governance, Risk, Compliance) assistant specialized in security frameworks.
Answer questions based on the provided context from security frameworks and controls.
Always cite the specific framework and control IDs when referencing requirements.
Be concise and precise. If the context doesn't contain enough information, say so clearly."""

    def __init__(
        self,
        model: str = config.OLLAMA_LLM_MODEL,
        base_url: str = config.OLLAMA_BASE_URL,
    ):
        import httpx

        self.model = model
        self.base_url = base_url
        self.client = httpx.Client(timeout=120)

    def generate(self, prompt: str, context: str) -> str:
        messages = self._build_messages(prompt, context)
        resp = self.client.post(
            f"{self.base_url}/api/chat",
            json={"model": self.model, "messages": messages, "stream": False},
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    def stream(self, prompt: str, context: str) -> Iterator[str]:
        import httpx

        messages = self._build_messages(prompt, context)
        with httpx.stream(
            "POST",
            f"{self.base_url}/api/chat",
            json={"model": self.model, "messages": messages, "stream": True},
            timeout=120,
        ) as resp:
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line)
                    if content := data.get("message", {}).get("content"):
                        yield content

    def _build_messages(self, prompt: str, context: str) -> list[dict]:
        return [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {prompt}"},
        ]


# ============================================================================
# Stub LLM (for when no LLM is available)
# ============================================================================


class StubLLM:
    """Stub LLM that just returns the context - useful for retrieval-only mode."""

    def generate(self, prompt: str, context: str) -> str:
        return f"[No LLM configured - showing retrieved context]\n\n{context}"

    def stream(self, prompt: str, context: str) -> Iterator[str]:
        yield self.generate(prompt, context)


# ============================================================================
# Factory functions
# ============================================================================


def get_embedder() -> Embedder:
    """Get the configured embedder."""
    if config.USE_OLLAMA_EMBED:
        try:
            embedder = OllamaEmbedder()
            # Test connection
            _ = embedder.dimensions
            return embedder
        except Exception as e:
            print(
                f"[warn] Ollama embedder failed ({e}), falling back to sentence-transformers"
            )

    return SentenceTransformerEmbedder()


def get_llm() -> LLM:
    """Get the configured LLM."""
    try:
        import httpx

        # Check if Ollama is running
        resp = httpx.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            return OllamaLLM()
    except Exception:
        pass

    print("[info] Ollama not available, running in retrieval-only mode")
    return StubLLM()


def is_ollama_available() -> bool:
    """Check if Ollama server is reachable."""
    try:
        import httpx

        resp = httpx.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False
