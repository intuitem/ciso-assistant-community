# Split into build and runtime stages so the runtime image carries only the
# interpreter, the venv and the source -- no uv, no build caches. This is also
# what makes a Docker Hardened Image swap a two-argument change:
#   --build-arg PYTHON_BUILD_IMAGE=dhi.io/python:3.14-dev
#   --build-arg PYTHON_RUNTIME_IMAGE=dhi.io/python:3.14
# Nothing here needs apt, a shell or a named user, which is what the backend
# image cannot say.
ARG PYTHON_BUILD_IMAGE=python:3.14-slim
ARG PYTHON_RUNTIME_IMAGE=python:3.14-slim

FROM ${PYTHON_BUILD_IMAGE} AS builder

# UV_PYTHON_DOWNLOADS=never: if the base ever stops satisfying requires-python,
# fail the build loudly instead of silently fetching a standalone CPython and
# leaving the image's own interpreter unused.
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

# COPY preserves the host's modes, so a source tree checked out under a
# restrictive umask ships a directory the runtime user cannot traverse.
# Normalising here also lets the image run as any uid -- there is no named user
# to match, which is what a distroless runtime needs.
RUN chmod -R a+rX /code

FROM ${PYTHON_RUNTIME_IMAGE}

ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PATH="/code/.venv/bin:$PATH"

WORKDIR /code

COPY --from=builder /code /code

# The server binds 0.0.0.0 inside the container and is not published to the
# host: reachability is the reverse proxy's job, so TLS terminates once, in
# front, and CA_MCP_ALLOWED_HOSTS can name the public FQDN the client actually
# sends. Publishing this port directly would expose a plaintext, credential-
# bearing endpoint.
ENV CA_MCP_TRANSPORT=streamable-http \
  CA_MCP_HOST=0.0.0.0 \
  CA_MCP_PORT=8001

EXPOSE 8001

# Exec form: a distroless runtime has no shell for the default shell form.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import socket,os; s=socket.create_connection(('127.0.0.1', int(os.environ.get('CA_MCP_PORT','8001'))), 3); s.close()"]

ENTRYPOINT ["python", "-m", "ca_mcp.server"]
