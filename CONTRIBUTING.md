# How to contribute

For the full contribution guide — development environment setup, coding standards, and the review process — see the [contributing documentation](https://intuitem.gitbook.io/ciso-assistant/product-docs/contributing/contributing). The notes below cover the essentials.

## Did you find a bug?

- **Do not open up a GitHub issue if the bug is a security vulnerability**, and instead to refer to our [security policy](SECURITY.md).
- Check that the bug was not previously reported on Github issues (see above).
- If it's the case, please upvote the issue and provide any relevant additional information.

## Do you have a fix for an issue, bug or typo?

- Open a pull request with the patch and the team will review it.
- Make sure that you've run a PEP8 formatter and SAST.
- If dependencies are involved, make sure it's not breaking the app and do not have any known vulnerabilities.

## Do you have an idea or feature request?

- Use the discussion space above or reach out through email: contact[at]intuitem.com to see how we can help each other in an optimal way.

## Do you want to contribute to the code?

- Please check our Contributor Licence Agreement first. Our bot will ask you to sign it on first contribution.

## Testing

- As major new functionality is added to the project, tests covering that functionality should be added to the automated test suite in the same pull request. This applies to bug fixes too: a regression test guards against the bug coming back.
- Run the suites locally before opening a PR:
  - Backend (Django/pytest): `uv run pytest` (in `backend/`)
  - Frontend unit tests (Vitest): `pnpm run test` (in `frontend/`)
  - Frontend end-to-end tests (Playwright): `./tests/e2e-tests.sh` (in `frontend/`)
- These suites also run in CI on every pull request and must pass before a change can be merged.

## Do you want to create and share a library?

- Have a look to the tools directory and its readme. A python script will help you create your library very simply from an Excel file. To share it with the community, make a PR, or contact us if you are not familiar with Github.
