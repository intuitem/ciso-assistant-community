---
description: How to submit a bug fix or a new feature to CISO Assistant
---

# Contributing code

CISO Assistant is open source and welcomes patches — bug fixes, performance improvements, new features, refactors, tests. This page walks through the submission flow and what reviewers look for.

## Before you start

- **Found a bug?** Search [the issues](https://github.com/intuitem/ciso-assistant-community/issues) first. If it already exists, upvote it and add context. If it's a security vulnerability, **do not open a public issue** — see [SECURITY.md](https://github.com/intuitem/ciso-assistant-community/blob/main/SECURITY.md).
- **Working on a feature?** Open a discussion or reach out at `contact[at]intuitem.com` before sinking time into an implementation. Some areas have ongoing work that's not yet visible in the repo, and we'd rather align early than turn down a finished PR.
- **Contributor License Agreement.** Required on first contribution; the CLA-assistant bot will prompt you when you open your first PR.

## Setting up your environment

Follow the [Local installation guide](../installation/local.md) to get a development instance running. Briefly:

- **Backend:** Python 3.14+, Poetry 2.0+, run `poetry install` then `manage.py migrate` and `manage.py runserver`.
- **Frontend:** Node 22+, pnpm 9.0+, run `pnpm install` then `pnpm run dev`.

A virtual environment is kept at the repo root (`.venv/`) — you can invoke `.venv/bin/python` directly.

## Coding conventions

- **Backend.** Follow PEP 8. Run a formatter (`ruff format` / `black`) before pushing. Run an SAST tool of your choice on any dependency change.
- **Frontend.** Use Svelte 5 syntax. Run `pnpm run lint` and `pnpm run format` before pushing.
- **Migrations.** Generate them with `manage.py makemigrations` and commit the file.
- **Dependencies.** Double-check anything new for known vulnerabilities; pin sensibly; mention added deps in the PR description.
- **Internal naming.** When a user-facing term differs from the model name (e.g. **Audit** ↔ `ComplianceAssessment`, **Domain** ↔ `Folder`), keep the user-facing term in UI copy and the internal name in code comments — don't leak internal names into the UI.

## Conventional commits

Commit messages and PR titles follow [Conventional Commits](https://www.conventionalcommits.org/). Use lowercase, include a scope where relevant:

| Type | When to use |
|---|---|
| `feat` | new user-visible capability |
| `fix` | bug fix |
| `chore` | maintenance with no production-code impact |
| `refactor` | code change that neither fixes a bug nor adds a feature |
| `perf` | performance-focused refactor |
| `docs` | documentation update |
| `test` | adding or updating tests |
| `ci` | CI configuration changes |
| `build` | build system or external dependency changes |

A `!` after the type marks a breaking change (`feat!:` or `feat(api)!:`). Breaking changes drive semantic-version bumps, so reviewers will check that the marker is set when it should be.

PRs are squash-merged, so the PR title becomes the squash-commit subject. Reviewers may rename PR titles before merge to enforce the convention.

## Tests

- Backend: `poetry run pytest` (or `.venv/bin/python -m pytest`) from the `backend/` directory.
- Frontend unit: `pnpm run test` from `frontend/`.
- Frontend e2e: `./tests/e2e-tests.sh` from `frontend/`.
- For UI changes, also start the dev server and click through the feature you touched — automated tests don't catch every regression.

## Opening the pull request

- Branch off `main` and keep the PR focused — one logical change per PR. Two unrelated fixes belong in two PRs.
- Describe the **why** in the PR body, link the issue if there is one, and attach screenshots for UI changes.
- Add a "Test plan" section listing what you verified.
- Accept the CLA when the bot asks.

## Related

- [Conventional Commits convention in the repo](https://github.com/intuitem/ciso-assistant-community/blob/main/conventional_commits.md)
- [Repository CONTRIBUTING.md](https://github.com/intuitem/ciso-assistant-community/blob/main/CONTRIBUTING.md)
- [Contributor License Agreement](https://github.com/intuitem/ciso-assistant-community/blob/main/Contributor%20License%20Agreement.md)
- [Security policy](https://github.com/intuitem/ciso-assistant-community/blob/main/SECURITY.md)
