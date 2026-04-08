FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy \
  PATH="/code/.venv/bin:$PATH" \
  DJANGO_SETTINGS_MODULE=enterprise_core.settings

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

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

COPY backend/pyproject.toml backend/uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=cache,target=/root/.cache/pip \
    uv sync --locked --no-dev \
  && .venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-deps \
  && .venv/bin/pip uninstall -y cuda-bindings cuda-pathfinder cuda-toolkit \
     nvidia-cublas nvidia-cuda-cupti nvidia-cuda-nvrtc nvidia-cuda-runtime \
     nvidia-cudnn-cu13 nvidia-cufft nvidia-cufile nvidia-curand nvidia-cusolver \
     nvidia-cusparse nvidia-cusparselt-cu13 nvidia-nccl-cu13 nvidia-nvjitlink \
     nvidia-nvshmem-cu13 nvidia-nvtx triton 2>/dev/null

COPY backend /code/
COPY enterprise/backend/enterprise_core /code/enterprise_core
COPY backend/startup.sh /code/

EXPOSE 8000
ENTRYPOINT ["bash", "startup.sh"]
