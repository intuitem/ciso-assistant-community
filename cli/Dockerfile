# Docker Hardened Images via the GHCR mirror, not dhi.io: DHI's free tier serves
# anonymous pulls, so dhi.io 401s for anyone logged in to Docker Hub.
ARG PYTHON_BUILD_IMAGE=ghcr.io/intuitem/ciso-assistant-community/mirror/dhi-python:3.14-dev
ARG PYTHON_RUNTIME_IMAGE=ghcr.io/intuitem/ciso-assistant-community/mirror/dhi-python:3.14

FROM ${PYTHON_BUILD_IMAGE} AS builder

# UV_PYTHON_DOWNLOADS=never: fail loudly rather than silently sideline the base interpreter
ENV PYTHONDONTWRITEBYTECODE=1 \
  UV_LINK_MODE=copy \
  UV_NO_SYNC=1 \
  UV_PYTHON_DOWNLOADS=never

COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /bin/

WORKDIR /code

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --locked --no-dev

#watch out for local files during dev and maintenance of .dockerignore
COPY . .

# COPY preserves host modes; normalise so any uid can traverse (distroless has no named user)
RUN chmod -R a+rX /code

FROM ${PYTHON_RUNTIME_IMAGE}

ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PATH="/code/.venv/bin:$PATH"

WORKDIR /code

COPY --from=builder /code /code

# Binds 0.0.0.0 inside the container only; never published to the host, the proxy fronts it
ENV CA_MCP_TRANSPORT=streamable-http \
  CA_MCP_HOST=0.0.0.0 \
  CA_MCP_PORT=8001

EXPOSE 8001

# Exec form: no shell in a distroless runtime
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import socket,os; s=socket.create_connection(('127.0.0.1', int(os.environ.get('CA_MCP_PORT','8001'))), 3); s.close()"]

ENTRYPOINT ["python", "-m", "ca_mcp.server"]
