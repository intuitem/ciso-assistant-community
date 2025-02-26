## Why

Based on the established documentation around [Conventional Commits](https://www.conventionalcommits.org) and the recommendations made in [#1334](https://github.com/intuitem/ciso-assistant-community/issues/1334), we have decided to adopt this principle using the following guidelines:

- Since v2, we have exclusively used squash merges, which has been beneficial so far. Therefore, we will continue to use this as the foundation for our workflow.
- Semantic versioning is **mandatory** for Pull Requests, particularly the use of `!` for breaking changes.
- Semantic commit messages are **recommended** for individual commits, as they will be included in the PR description after a squash merge.
- Renaming PR titles is significantly easier than reworking commits. While we encourage all contributors to adhere to the convention, reviewers can make necessary adjustments as needed.
- Reviewers must ensure consistency with the convention during the merge process.

## Convention

- Use lowercase for all commit messages.
- Include a scope when relevant. For example, use `feat(lib)` when adding a new framework or library.
- The following commit types are supported:
  - `fix`: Bug fixes
  - `feat`: New features
  - `chore`: Maintenance tasks or changes that don't affect production code
  - `refactor`: Code changes that neither fix bugs nor add features
  - `perf`: special refactor commits, that improve performance
  - `docs`: Documentation updates or improvements
  - `test`: Adding or updating tests
  - `ci`: Changes to the CI configuration or scripts
  - `build`: Changes that affect the build system or external dependencies
