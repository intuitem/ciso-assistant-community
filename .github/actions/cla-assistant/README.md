# Vendored CLA Assistant action

Local copy of [`contributor-assistant/github-action`](https://github.com/contributor-assistant/github-action)
at tag **`v2.6.1`** (commit `ca4a40a`). Upstream was archived (read-only) on
2026-03-23, so we vendor it here to remove the dependency on an unmaintained
external action while keeping behaviour identical.

Used by `.github/workflows/cla.yml` via `uses: ./.github/actions/cla-assistant`.

## Provenance — the committed `dist/` is verified, not opaque

`dist/index.js` is the bundler output (`tsc && ncc build`) and is what GitHub
actually executes. It was reproduced byte-for-byte from the `src/` in this
directory, so it is not a blob you have to trust blindly:

```
sha256(dist/index.js) = a44111084c0d4782206c04b4276292f7fec6d1f7a33525512fbeef3242079dfb
```

To re-verify locally:

```bash
npm ci        # deterministic install from package-lock.json
npm run build # tsc && ncc build -> dist/index.js
shasum -a 256 dist/index.js   # must equal the hash above
```

The `cla-assistant-dist-check` CI workflow runs this on every change to this
directory and fails if the committed `dist/` drifts from `src/`.

## Updating

Edit `src/`, run `npm run build`, commit the regenerated `dist/`. The CI guard
enforces that the two stay in sync.

## License

Apache-2.0 (SAP). See `LICENSE`.
