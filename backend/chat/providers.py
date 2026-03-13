"""
LLM and embedding provider abstraction.
Supports Ollama (default) with sentence-transformers fallback for embeddings.
"""

from typing import Protocol, Iterator
import json
import logging

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    """Interface for embedding providers."""

    @property
    def dimensions(self) -> int: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class LLM(Protocol):
    """Interface for LLM providers."""

    def generate(
        self, prompt: str, context: str, history: list[dict] | None = None
    ) -> str: ...

    def stream(
        self, prompt: str, context: str, history: list[dict] | None = None
    ) -> Iterator[str]: ...


class SentenceTransformerEmbedder:
    """Local embeddings using sentence-transformers. No external service needed."""

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
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


class OllamaEmbedder:
    """Embeddings using Ollama server."""

    def __init__(
        self,
        model: str = "snowflake-arctic-embed2",
        base_url: str = "http://localhost:11434",
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
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        resp = self.client.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.model, "prompt": text},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]


class OllamaLLM:
    """LLM using Ollama server."""

    DEFAULT_SYSTEM_PROMPT = (
        "You are a GRC (Governance, Risk, Compliance) assistant specialized in security frameworks. "
        "Answer questions based on the provided context from security frameworks, controls, risk scenarios, and assessments. "
        "Always cite specific framework and control IDs when referencing requirements. "
        "Be concise and precise. If the context doesn't contain enough information, say so clearly."
    )

    def __init__(
        self,
        model: str = "mistral",
        base_url: str = "http://localhost:11434",
        system_prompt: str = "",
    ):
        import httpx

        self.model = model
        self.base_url = base_url
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.client = httpx.Client(timeout=120)

    def generate(
        self, prompt: str, context: str, history: list[dict] | None = None
    ) -> str:
        messages = self._build_messages(prompt, context, history)
        resp = self.client.post(
            f"{self.base_url}/api/chat",
            json={"model": self.model, "messages": messages, "stream": False},
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    def stream(
        self, prompt: str, context: str, history: list[dict] | None = None
    ) -> Iterator[str]:
        import httpx

        messages = self._build_messages(prompt, context, history)
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

    def _build_messages(
        self, prompt: str, context: str, history: list[dict] | None = None
    ) -> list[dict]:
        messages = [{"role": "system", "content": self.system_prompt}]

        # Include conversation history (excluding the current message)
        if history:
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})

        # Current user message with RAG context
        user_msg = f"Context:\n{context}\n\nQuestion: {prompt}" if context else prompt
        messages.append({"role": "user", "content": user_msg})
        return messages


class StubLLM:
    """Fallback when no LLM is available — returns retrieval results only."""

    def generate(
        self, prompt: str, context: str, history: list[dict] | None = None
    ) -> str:
        return f"[No LLM configured — showing retrieved context]\n\n{context}"

    def stream(
        self, prompt: str, context: str, history: list[dict] | None = None
    ) -> Iterator[str]:
        yield self.generate(prompt, context)


def get_chat_settings() -> dict:
    """Load chat/LLM settings from global_settings."""
    from global_settings.models import GlobalSettings

    try:
        gs = GlobalSettings.objects.filter(name="general").first()
        if gs and isinstance(gs.value, dict):
            return {
                "ollama_base_url": gs.value.get(
                    "ollama_base_url", "http://localhost:11434"
                ),
                "ollama_model": gs.value.get("ollama_model", "mistral"),
                "ollama_embed_model": gs.value.get(
                    "ollama_embed_model", "snowflake-arctic-embed2"
                ),
                "embedding_backend": gs.value.get(
                    "embedding_backend", "sentence-transformers"
                ),
                "chat_system_prompt": gs.value.get("chat_system_prompt", ""),
            }
    except Exception:
        pass
    return {
        "ollama_base_url": "http://localhost:11434",
        "ollama_model": "mistral",
        "ollama_embed_model": "snowflake-arctic-embed2",
        "embedding_backend": "sentence-transformers",
        "chat_system_prompt": "",
    }


def get_embedder() -> Embedder:
    """Get the configured embedder based on global settings."""
    settings = get_chat_settings()

    if settings["embedding_backend"] == "ollama":
        try:
            embedder = OllamaEmbedder(
                model=settings["ollama_embed_model"],
                base_url=settings["ollama_base_url"],
            )
            _ = embedder.dimensions  # Test connection
            return embedder
        except Exception as e:
            logger.warning(
                "Ollama embedder failed (%s), falling back to sentence-transformers", e
            )

    return SentenceTransformerEmbedder()


def get_llm() -> LLM:
    """Get the configured LLM based on global settings."""
    settings = get_chat_settings()

    try:
        import httpx

        resp = httpx.get(f"{settings['ollama_base_url']}/api/tags", timeout=5)
        if resp.status_code == 200:
            return OllamaLLM(
                model=settings["ollama_model"],
                base_url=settings["ollama_base_url"],
                system_prompt=settings["chat_system_prompt"],
            )
    except Exception:
        pass

    logger.info("Ollama not available, running in retrieval-only mode")
    return StubLLM()


def is_ollama_available() -> bool:
    """Check if Ollama server is reachable."""
    settings = get_chat_settings()
    try:
        import httpx

        resp = httpx.get(f"{settings['ollama_base_url']}/api/tags", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False
