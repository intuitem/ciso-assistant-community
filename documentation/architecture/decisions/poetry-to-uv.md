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
- PyTorch is pinned to its CPU index via `[tool.uv.sources]`; the force-reinstall/purge hack is gone.
- Usage stays close to Poetry (`uv add`, `uv run`, lockfiles), so adoption cost was low.
- `poetry.lock` → `uv.lock`; build backend moved to `setuptools`.
