# Move backend dependency management from Poetry to uv

- Status: Accepted
- Deciders: @ab-smith, @eric-intuitem, @mohamed-hacene, @nas-tabchiche, @axxiar

## Context

The backend is split into a community and an enterprise edition, the latter copying and overriding the former. Under Poetry, working across this split locally required `poetry shell` just to access enterprise files while using community dependencies for local development.

Separately, Poetry couldn't reliably pin PyTorch to its CPU-only index, so Dockerfiles installed the full CUDA build (GPU + CPU) then force-reinstalled and manually purged it via raw `pip`. [More details on this Poetry issue](https://github.com/python-poetry/poetry/issues/6409), [link to the actual fix](https://github.com/intuitem/ciso-assistant-community/commit/eddccd139aad080bb88a9bf3242dbc42641e8cd2).

UV showed up as an easy, faster and (almost) drop-in replacement that could solve these issues.

## Decision

We will replace Poetry with uv as the backend's dependency and environment manager, across CI, Docker and development.

## Consequences

- No more `poetry shell`; local dev works across the community/enterprise split directly.
- Faster installs and resolution, locally and in CI/Docker.
- Usage stays close to Poetry (`uv add`, `uv run`, lockfiles), so adoption cost was low.
- `poetry.lock` → `uv.lock`; build backend moved to `setuptools`.

## Security considerations

The decision changes how dependencies are resolved and installed, so it touches the supply chain. It does not widen it:

- `uv.lock` records a hash for every artifact, and Docker images and CI install with `uv sync --locked`, which fails when the lock is out of date with `pyproject.toml` instead of resolving anew.
- Packages come from PyPI only; no extra index is configured, so no dependency can be shadowed from a second index.
- The image's interpreter is the base image's own (`UV_PYTHON_DOWNLOADS=never`), and the venv is not re-synced at runtime (`UV_NO_SYNC=1`).

Accepted risk: a malicious release that is locked in a dependency update still installs. Reviewing lock changes is the mitigation, as it was with Poetry.
