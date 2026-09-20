---
name: product-docs-screenshots
description: |
  Generate and refresh the screenshots in product-docs/ from a real, running CISO Assistant instance, and wire them into the Markdown. Use when:
  (1) User asks to illustrate, add screenshots to, or update a product-docs page
  (2) User ships a feature and asks to document it ("document X", "add docs for X", "update the product docs")
  (3) A UI change made existing screenshots stale ("refresh the screenshots", "the docs images are out of date")
  (4) User asks for annotated / step-by-step images for a guide page

  Covers: the deterministic demo fixture (seed_docs_demo), the Playwright capture harness, annotated callout shots, figure placement and caption grounding.
---

# Product-docs screenshots

Screenshots in `product-docs/` are **generated, not taken by hand**. One command
rebuilds the demo database, starts the stack, and re-captures every shot. Two
runs produce byte-identical PNGs, so a diff means the UI changed.

Never paste a hand-captured screenshot into `product-docs/`. If an image is
needed, add it to the manifest so the next person can regenerate it.

## The loop

Work through these in order. Do not skip step 5.

### 1. Find the doc page

Locate the page under `product-docs/` and check `SUMMARY.md` — GitBook only
renders pages listed there. Read the page first and pick the section the image
belongs to; a figure at the top of a concept page is usually the wrong place.

### 2. Check the fixture covers the feature

`backend/core/management/commands/seed_docs_demo.py` seeds one demo domain
(`Northwind Trading`) with perimeters, assets, applied controls, three audits on
ISO 27001:2022, and a risk assessment with six scenarios.

If the page documents a module the fixture does not cover (EBIOS RM, BIA,
incidents, tasks, vulnerabilities, TPRM, privacy, findings, quantitative risk),
**extend the seed first** — a screenshot of an empty list is worse than none.
Follow the conventions already in the file:

- seed the RNG (`random.seed(SEED)`) and use a fixed vocabulary
- derive dates from `TODAY`, never `date.today()`
- add the new model to `freeze_timestamps` with an explicit natural sort key

There are `populate_*` management commands for several modules, but they do
**not** seed the RNG, so their output is different on every run. Do not call
them from the screenshot path without fixing that first.

### 3. Add a manifest entry

In `frontend/tests/docs-screenshots/manifest.ts`:

```ts
{
  slug: 'audit-detail',              // → product-docs/.gitbook/assets/audit-detail.png
  url: '/compliance-assessments',
  usedBy: ['concepts/audits.md'],    // so a stale shot is traceable to its pages
  then: openDetail('compliance-assessments', 'AUD.2026.01'),
  clip: (page) => page.getByRole('heading', { name: '…' })
                      .locator('xpath=ancestor::div[contains(@class,"card")][1]')
}
```

- Prefer `clip` for concept pages — a whole-viewport shot of a detail route is
  mostly metadata the prose already covers.
- `fullPage: true` for long list pages.
- For a guide that walks through steps, use `annotate` to outline the controls
  and number them so the prose can refer to them:

```ts
annotate: (page) => [
  { at: page.getByRole('link', { name: 'Action plan' }).first(), label: '1' },
  { at: page.getByRole('button', { name: 'Add risk scenario' }).first(), label: '2' }
]
```

### 4. Run the harness

```bash
cd frontend
./tests/docs-screenshots/run.sh --reseed                       # everything
./tests/docs-screenshots/run.sh --keep-up -- --grep audit      # one shot, servers left up
```

It uses its own database and ports (8273 / 5273) and must not be pointed at the
e2e stack — `e2e-tests.sh` owns 8173 and `test-database.sqlite3`, and two runs
sharing a SQLite file corrupt each other.

### 5. Read the PNG before writing the caption

**Always open the generated image with the Read tool.** Captions must describe
what is actually on screen. This step exists because it is genuinely easy to
write a caption for a column that is not in the table — a generated screenshot
looks authoritative even when the sentence beside it is invented.

While reading it, also check the shot is worth shipping: right record selected,
no empty charts, no placeholder `--` columns dominating the frame.

### 6. Insert the figure

```html
<figure><img src="../.gitbook/assets/<slug>.png" alt=""><figcaption><p>Caption</p></figcaption></figure>
```

Adjust `../` depth for the page's directory. Quote any UI label in the caption
**verbatim from `frontend/messages/en.json`** — if the string is not there, the
button does not say that.

### 7. Verify

- every `src="...png"` in the page resolves on disk
- re-run the harness twice and confirm the PNGs are byte-identical
- cite the `file:line` sources you used in the chat reply, not in the doc body

## Traps

These all cost time to rediscover.

| Trap | What happens | Do this |
| --- | --- | --- |
| `devices['Desktop Chrome']` carries its own viewport | project-level `use` silently overrides the config viewport; shots come out 1280×720 | re-declare viewport *after* the device spread |
| Row names in `ModelTable` are not links | matching a row by visible text, or taking the first detail anchor, lands on the wrong record | match the row by seeded `ref_id` via `openDetail()` |
| Identical `created_at` values | `BaseModelViewSet.ordering = ["created_at"]` and `SmartOrderingFilter` appends `pk` (a random UUID) as tiebreaker, so lists shuffle on every rebuild | stagger the stamps; give each model an explicit natural sort key |
| Some detail routes nest two `<main>` elements | strict-mode locator violation | `.first()` |
| `wrapperClass` lands on the inner element | a clip loses the axis titles or legend | clip the target's parent |
| ECharts canvases | drifted once by 114 px with identical data | compare chart shots with a pixel threshold, not a checksum |
| macOS + WeasyPrint | backend dies on `libgobject` at import | `run.sh` exports `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` |
| A git worktree has no `.venv` | the repo-root venv does not carry | `run.sh` falls back to `uv run python3`; or set `DOCS_SHOTS_PYTHON` |

## Reference

`frontend/tests/docs-screenshots/README.md` holds the harness contract — the
determinism table, the config choices and the known caveats. Read it before
changing the config or the capture spec.
