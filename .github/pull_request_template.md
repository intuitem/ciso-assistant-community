<!--
PR title must follow Conventional Commits (squash-merged → title becomes the commit subject):
  feat | fix | chore | refactor | perf | docs | test | ci | build   (lowercase, scope optional, `!` for breaking)
  e.g. feat(lib): add NIS2 framework   |   fix(api): correct residual risk validation
Full guide: product-docs/contributing/code.md
-->

## What & why

<!-- What does this change do, and why? Link the issue if there is one. -->

Closes #

## Test plan

<!-- What you ran/clicked to verify. Attach screenshots for UI changes. -->

## Checklist

<!-- Keep the sections that apply, delete the rest. Tests and docs are part of "done" — tick them when relevant, or note why they aren't. -->

- [ ] PR title follows Conventional Commits (`!` set if this is a breaking change)
- [ ] One focused change, branched off `main`
- [ ] CLA accepted (first contribution only)

### Backend — if you touched `backend/`
- [ ] `ruff format` run, no new linter errors
- [ ] Migrations generated with `makemigrations` and committed (or none needed)
- [ ] New dependencies checked for known vulnerabilities and called out above

### Frontend — if you touched `frontend/`
- [ ] Svelte 5 syntax; `pnpm run lint` and `pnpm run format` run
- [ ] New/changed UI strings added to `frontend/messages/en.json` (keep keys, preserve `{tokens}`)
- [ ] Clicked through the change in the dev server; screenshots attached for UI changes

### Other — libraries, CI, infra
- [ ] Library changes built via the `tools/` script
- [ ] CI / build changes run green

### Tests & documentation — definition of done
- [ ] Tests added or updated and passing locally — backend `poetry run pytest`, frontend `pnpm run test` / `./tests/e2e-tests.sh` *(if relevant)*
- [ ] Regression test added for bug fixes *(if relevant)*
- [ ] `product-docs/` updated, new pages listed in `SUMMARY.md`, vocabulary terms added *(if relevant)*
- [ ] No tests or docs needed for this change — why:
