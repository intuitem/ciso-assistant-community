# Vendored CLA Assistant action (patched fork)

Local, **patched** copy of
[`contributor-assistant/github-action`](https://github.com/contributor-assistant/github-action)
`v2.6.1` (commit `ca4a40a`). Upstream was archived (read-only) on 2026-03-23,
so we vendor it here to remove the dependency on an unmaintained external
action and to patch the vulnerable, stale dependencies it shipped with.

Used by `.github/workflows/cla.yml` via `uses: ./.github/actions/cla-assistant`.

## Changes vs upstream v2.6.1

- **Pruned dead dependencies** never imported by `src/`: `@octokit/rest`,
  `actions-toolkit`, `husky`, `node-fetch` (and dev-only `jest`/`ts-jest`/
  `@octokit/types`). This removed the bulk of the CVE surface.
- **Bumped** `@actions/github` `^4 → ^6` and `@actions/core` `→ ^1.11`, with an
  `overrides` pin of `undici` to `^6.26.0` (the `@actions/*` chain otherwise
  resolves a vulnerable `undici`).
- **Inlined** the single `lodash.escapeRegExp` use in `checkAllowList.ts` as a
  native helper, dropping `lodash` entirely.
- **Updated REST call sites** `octokit.<resource>` → `octokit.rest.<resource>`
  (required by the newer Octokit) and added type-faithful null guards.
- **Retargeted the runtime** `node20 → node24` in `action.yml`.

Result: `npm audit` reports **0 vulnerabilities** (prod and dev).

## Provenance — the committed `dist/` is reproducible, not opaque

`dist/index.js` is the bundler output (`tsc && ncc build`) and is what GitHub
actually executes. It is reproduced deterministically from the `src/` and
`package-lock.json` in this directory, so it is not a blob to trust blindly:

```
sha256(dist/index.js) = b0805f1080ae56759f93ca0bf76adca06d9c1a0d71d0d3a755c0139767f89450
```

To re-verify locally (Node 24):

```bash
npm ci        # deterministic install from package-lock.json
npm run build # tsc && ncc build -> dist/index.js
shasum -a 256 dist/index.js   # must equal the hash above
```

The `cla-assistant-dist-check` CI workflow runs this on every change to this
directory and fails if the committed `dist/` drifts from `src/`.

## Updating

Edit `src/`, run `npm run build`, commit the regenerated `dist/`. The CI guard
enforces that the two stay in sync. Keep deps current with the Dependabot entry
scoped to this directory.

## License

Apache-2.0 (SAP). See `LICENSE`.
