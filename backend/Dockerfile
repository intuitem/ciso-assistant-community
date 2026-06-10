FROM python:3.14-slim

# UV_NO_SYNC=1: prevent `uv run` from auto-syncing at runtime (caused startup-docker-compose-test CI to fail);
#   the venv is built once at image build (uv sync --locked --no-dev)
ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  UV_LINK_MODE=copy \
  UV_NO_SYNC=1 \
  PATH="/code/.venv/bin:$PATH"

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

RUN --mount=type=cache,target=/root/.cache/uv \
  --mount=type=cache,target=/root/.cache/pip \
  uv sync --locked --no-dev \
  && uv pip install torch --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-deps \
  && uv pip uninstall cuda-bindings cuda-pathfinder cuda-toolkit \
  nvidia-cublas nvidia-cuda-cupti nvidia-cuda-nvrtc nvidia-cuda-runtime \
  nvidia-cudnn-cu13 nvidia-cufft nvidia-cufile nvidia-curand nvidia-cusolver \
  nvidia-cusparse nvidia-cusparselt-cu13 nvidia-nccl-cu13 nvidia-nvjitlink \
  nvidia-nvshmem-cu13 nvidia-nvtx triton 2>/dev/null

#watch out for local files during dev and maintenance of .dockerignore
COPY . .

RUN groupadd -g 1001 app && useradd -u 1001 -g 1001 -m -s /bin/bash app
# USER app  # not activated by default to keep compatibility

EXPOSE 8000
ENTRYPOINT ["uv", "run", "bash", "startup.sh"]
