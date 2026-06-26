"""Model identifiers for the local embedding and reranking backends.

Kept dependency-free (no Django, no heavy imports) so the Docker build can import
it to pre-bake the models offline (see backend/Dockerfile) without pulling the rest
of the app. Single source of truth shared by the runtime code and the image bake.
"""

DEFAULT_EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
