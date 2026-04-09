# AI Chat Mode — Setup Guide

> Setup guide for enabling the AI assistant in CISO Assistant.

## 0. Enable the Chat Module

The chat feature is **disabled by default**. Set the `ENABLE_CHAT` environment variable to enable it:

```bash
export ENABLE_CHAT=true
```

For Docker deployments, add it to your `docker-compose.yml` or `.env` file. This controls:
- Visibility of the `chat_mode` feature flag in Settings
- Visibility of the Chat/AI settings section (LLM provider, model, etc.)
- Signal handlers for RAG indexing
- Knowledge graph pre-warming at startup

Without `ENABLE_CHAT=true`, the chat app is installed (for migrations) but completely dormant.

---

## Prerequisites

| Component | Purpose | Required? |
|-----------|---------|-----------|
| **LLM server** | Local LLM inference — [Ollama](https://ollama.com), [LM Studio](https://lmstudio.ai), [MLX](https://github.com/ml-explore/mlx-examples/tree/main/llms/mlx_lm), or [llama.cpp](https://github.com/ggml-org/llama.cpp) | Yes (one of them) |
| **Qdrant** | Vector database for RAG | Yes |
| **Huey worker** | Background indexing tasks | Recommended |

---

## 1. Install & Start Services

### Ollama

```bash
# macOS
brew install ollama
ollama serve

# Pull a model (mistral is the default)
ollama pull mistral

# Optional: pull an embedding model
ollama pull snowflake-arctic-embed2
```

> You can use any model Ollama supports. Smaller models (mistral, phi3) work but are less reliable at tool selection. Larger models (llama3, mixtral) give better results.

### LM Studio

1. Download from [lmstudio.ai](https://lmstudio.ai)
2. Load a model and start the local server (default: `http://localhost:1234/v1`)
3. Set `llm_provider` to `openai_compatible` in settings (see step 3)

### MLX (macOS Apple Silicon)

Best performance on Mac — uses Metal natively.

```bash
pip install mlx-lm
mlx_lm.server --model mlx-community/gpt-oss-20b-MXFP4-Q4 --port 8080
```

Set `llm_provider` to `openai_compatible` and `openai_api_base` to `http://localhost:8080/v1`.

### llama.cpp

Lightweight, supports GGUF models.

```bash
brew install llama.cpp
llama-server -m ./models/your-model.gguf -c 8192 -ngl 999 --port 8081
```

Set `llm_provider` to `openai_compatible` and `openai_api_base` to `http://localhost:8081/v1`.

### Qdrant

```bash
docker run -d --name qdrant -p 6333:6333 -v qdrant_data:/qdrant/storage qdrant/qdrant
```

Default URL: `http://localhost:6333`. Override with the `QDRANT_URL` environment variable if needed.

---

## 2. Initialize the Vector Store

```bash
# Create the Qdrant collection with proper indexes
.venv/bin/python backend/manage.py init_qdrant

# If you need to reset it
.venv/bin/python backend/manage.py init_qdrant --recreate
```

### Index your data

```bash
# Index existing objects (risks, controls, assets, etc.)
.venv/bin/python backend/manage.py index_objects

# Index all framework libraries (150+ frameworks → Qdrant)
.venv/bin/python backend/manage.py index_libraries --sync
```

> `index_libraries` parses all YAML files in `backend/library/libraries/` and indexes requirement nodes, threats, and reference controls. This can take a few minutes.

### Start the background worker

New objects are indexed automatically via Django signals, but this requires Huey:

```bash
cd backend
uv run python manage.py run_huey -w 2 -k process
```

---

## 3. Enable Chat Mode & Configure Settings

Go to the **admin panel** or use the API to update settings.

### Enable the feature flag

In **Settings > Feature Flags**, enable **Chat Mode**.

### Configure the LLM

In **Settings > General**, set:

| Setting | Default | Description |
|---------|---------|-------------|
| `llm_provider` | `ollama` | `ollama` or `openai_compatible` |
| `ollama_base_url` | `http://localhost:11434` | Ollama server URL |
| `ollama_model` | `mistral` | Model name for chat generation |
| `ollama_embed_model` | `snowflake-arctic-embed2` | Model for embeddings (if using Ollama embeddings) |
| `embedding_backend` | `sentence-transformers` | `sentence-transformers` (CPU, no setup) or `ollama` |
| `openai_api_base` | `http://localhost:1234/v1` | For LM Studio / vLLM / llama.cpp |
| `openai_model` | _(empty)_ | Model identifier for OpenAI-compatible servers |
| `openai_api_key` | _(empty)_ | API key for authenticated endpoints (optional) |
| `chat_system_prompt` | _(empty)_ | Custom system prompt (overrides the built-in GRC prompt) |

---

## 4. Embedding Options

### Option A: Sentence-Transformers (zero setup)

Set `embedding_backend` to `sentence-transformers`. This uses `paraphrase-multilingual-MiniLM-L12-v2` locally on CPU. The model (~130 MB) downloads automatically on first use. Multilingual support included.

This is the default and requires no external service.

### Option B: Ollama Embeddings

Set `embedding_backend` to `ollama` and pull an embedding model:

```bash
ollama pull snowflake-arctic-embed2
```

Higher quality than sentence-transformers but requires the Ollama server to be running.

> If Ollama embeddings fail, the system automatically falls back to sentence-transformers.

---

## 5. Verify Everything Works

### Check the status endpoint

```
GET /api/chat/status/
```

Returns the health of the LLM and embedding backends.

### Check available models

```
GET /api/chat/ollama-models/
```

Lists models available on your Ollama server.

### Open the chat

Click the chat widget in the bottom-right corner of the app (only visible when chat mode is enabled).

---

## Troubleshooting

### Chat widget doesn't appear

- Check that `ENABLE_CHAT=true` is set in your environment
- Check that the `chat_mode` feature flag is enabled in Settings > Feature Flags
- Hard-refresh the browser (Ctrl+Shift+R)

### Chat settings section not visible

- `ENABLE_CHAT` env var must be set to `true` — the settings section is hidden otherwise

### "No LLM available" / responses are just raw context

The system degrades gracefully: if no LLM is reachable, it returns retrieved context without generation. Check:

- Ollama is running: `curl http://localhost:11434/api/tags`
- Or LM Studio server is running: `curl http://localhost:1234/v1/models`

### RAG returns no results

- Verify Qdrant is running: `curl http://localhost:6333/collections`
- Check the collection exists: `curl http://localhost:6333/collections/ciso_assistant`
- Re-run indexing: `python manage.py init_qdrant --recreate && python manage.py index_objects && python manage.py index_libraries --sync`

### Framework queries don't work

The knowledge graph builds lazily on first use from YAML files (~27s). If framework queries return empty results:

- Check that library YAML files exist in `backend/library/libraries/`
- The graph is independent of Qdrant — it reads YAML directly

### Tool selection is unreliable

Small models (< 7B params) struggle with function calling. Options:

- Use a larger model (`ollama pull mixtral` or `llama3`)
- The system has deterministic keyword-based pre-routing for common workflows (suggest controls, risk treatment, evidence guidance) that bypasses the LLM

---

## Maintenance

### Clean up old sessions

Chat sessions accumulate over time. Use the management command to purge old ones:

```bash
# Preview what would be deleted
.venv/bin/python backend/manage.py cleanup_sessions --days 90 --dry-run

# Delete sessions older than 90 days
.venv/bin/python backend/manage.py cleanup_sessions --days 90
```

Messages cascade-delete with their sessions.

---

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full design, diagrams, and component reference.
