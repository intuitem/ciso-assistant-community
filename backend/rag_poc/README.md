# RAG POC for CISO Assistant

A minimal proof-of-concept for RAG (Retrieval-Augmented Generation) over security frameworks.

## Quick Start

```bash
# Install dependencies
pip install qdrant-client sentence-transformers pyyaml httpx rich

# Optional: Install Ollama for local LLM
# https://ollama.ai/download
# ollama pull llama3.2
# ollama pull nomic-embed-text

# Index frameworks (uses sentence-transformers by default)
python index.py

# Query (uses Ollama if available, otherwise just retrieval)
python query.py "What are the requirements for access control?"

# Interactive mode
python query.py --interactive
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   YAML      │────▶│  Indexer    │────▶│   Qdrant    │
│  Libraries  │     │             │     │   (local)   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
┌─────────────┐     ┌─────────────┐            │
│   Query     │────▶│  Retriever  │◀───────────┘
│             │     │             │
└─────────────┘     └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    LLM      │ (optional)
                    │  (Ollama)   │
                    └─────────────┘
```

## Configuration

Environment variables:
- `OLLAMA_BASE_URL`: Ollama server URL (default: http://localhost:11434)
- `OLLAMA_EMBED_MODEL`: Embedding model (default: nomic-embed-text)
- `OLLAMA_LLM_MODEL`: LLM model (default: llama3.2)
- `USE_OLLAMA_EMBED`: Use Ollama for embeddings instead of sentence-transformers (default: false)

## Files

- `index.py` - Index framework YAML files into Qdrant
- `query.py` - Query the indexed frameworks
- `config.py` - Configuration and provider abstraction
- `providers.py` - Embedder and LLM provider implementations
