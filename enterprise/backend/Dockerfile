FROM python:3.14-slim

# UV_NO_SYNC=1: prevent `uv run` from auto-syncing at runtime; the venv is built once at image build (uv sync --locked --no-dev)
ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  UV_LINK_MODE=copy \
  UV_NO_SYNC=1 \
  PATH="/code/.venv/bin:$PATH" \
  DJANGO_SETTINGS_MODULE=enterprise_core.settings

COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /bin/

WORKDIR /code

RUN apt-get update && apt-get install -y \
  libyaml-cpp-dev \
  libffi-dev \
  libglib2.0-0 \
  pango-1.0 \
  libcairo2 \
  locales \
  tzdata \
  gettext \
  fontconfig \
  fonts-freefont-ttf \
  build-essential \
  python3-dev \
  python3-numpy \
  libjpeg-dev \
  zlib1g-dev \
  libmagic1 \
  bubblewrap \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/* \
  && locale-gen en_US.UTF-8 \
  && locale-gen ar_SA.UTF-8 \
  && locale-gen fr_FR.UTF-8 \
  && locale-gen pt_PT.UTF-8 \
  && locale-gen es_ES.UTF-8 \
  && locale-gen de_DE.UTF-8 \
  && locale-gen nl_NL.UTF-8 \
  && locale-gen it_IT.UTF-8 \
  && locale-gen pl_PL.UTF-8 \
  && locale-gen ro_RO.UTF-8 \
  && locale-gen hi_IN.UTF-8 \
  && locale-gen ur_PK.UTF-8 \
  && locale-gen cs_CZ.UTF-8 \
  && locale-gen sv_SE.UTF-8 \
  && locale-gen id_ID.UTF-8

COPY pyproject.toml uv.lock ./

# torch is pinned to the PyTorch CPU index in pyproject.toml/uv.lock, so the CUDA
# wheels are never resolved or downloaded — a plain locked sync is enough.
RUN --mount=type=cache,target=/root/.cache/uv \
  --mount=type=cache,target=/root/.cache/pip \
  uv sync --locked --no-dev

# Pre-bake the embedding and reranker models into the image so the AI works with no
# internet at runtime (otherwise sentence-transformers downloads them from HuggingFace
# on first use, which breaks fully offline / air-gapped instances).
# Model IDs come from chat/embedding_models.py (single source of truth). It is copied
# first so this layer re-bakes whenever the IDs change. Network is needed at BUILD time only.
COPY chat/embedding_models.py ./chat/embedding_models.py
ENV HF_HOME=/opt/hf-cache \
  SENTENCE_TRANSFORMERS_HOME=/opt/hf-cache
RUN uv run python -c "import chat.embedding_models as m; from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer(m.DEFAULT_EMBEDDING_MODEL); CrossEncoder(m.RERANKER_MODEL)" \
  && chown -R 1001:1001 /opt/hf-cache

# Force offline at runtime: the model is cached above and nothing else in the chat
# stack reaches HuggingFace (LLM and Ollama use their own URLs). Avoids a network
# round-trip on model load. Set AFTER the bake so the build can still download.
ENV HF_HUB_OFFLINE=1 \
  TRANSFORMERS_OFFLINE=1

COPY . /code/
COPY --from=enterprise_backend /enterprise_core /code/enterprise_core
COPY startup.sh /code/

RUN groupadd -g 1001 app && useradd -u 1001 -g 1001 -m -s /bin/bash app
# USER app  # not activated by default to keep compatibility

EXPOSE 8000
ENTRYPOINT ["uv", "run", "bash", "startup.sh"]
