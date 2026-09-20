# Documentation screenshots

Captures the images used by `product-docs/` from a real, logged-in instance
against a deterministic demo dataset. Two runs on the same checkout reproduce
every DOM-only capture byte for byte, so a diff means the UI changed — not that
someone re-ran the capture. Chart captures are compared with a small pixel
threshold instead; see the caveats below.

> **Do not name files in this directory `*.spec.ts` or `*.test.ts`.** The e2e
> workflow globs those patterns across the whole of `tests/`
> (`.github/workflows/functional-tests.yml`), and a screenshot spec swept into
> that matrix runs against the e2e stack with no demo data and no auth state —
> it burned 24 minutes before failing on PR #4866. Hence `capture.shots.ts`.

## Running

```bash
./tests/docs-screenshots/run.sh --reseed
```

The script starts its own backend (port 8273) and dev server (port 5273)
against `backend/db/docs-shots.sqlite3`, seeds the demo data, captures every
shot in `manifest.ts`, and writes to `product-docs/.gitbook/assets/<slug>.png`.

It does **not** reuse the e2e ports or database on purpose — `e2e-tests.sh`
owns 8173 and `test-database.sqlite3`, and two runs sharing a SQLite file
corrupt each other.

Capture a subset while iterating:

```bash
./tests/docs-screenshots/run.sh --keep-up -- --grep audit
```

## Adding a shot

Add an entry to `manifest.ts`:

```ts
{
  slug: 'audit-detail',              // → .gitbook/assets/audit-detail.png
  url: '/compliance-assessments',
  usedBy: ['concepts/audits.md'],    // so a stale shot is traceable to its pages
  then: openDetail('compliance-assessments', 'AUD.2026.01'),
  clip: (page) => page.getByRole('heading', { name: '…' })
                      .locator('xpath=ancestor::div[contains(@class,"card")][1]')
}
```

- `clip` is usually what a doc wants. A whole-viewport shot of a detail page is
  mostly metadata the prose already covers.
- Match rows by seeded `ref_id`, never by list position — row order is not
  guaranteed and you will silently screenshot the wrong record.
- `fullPage: true` for long list pages.

## What keeps the output stable

| Source of drift                     | How it is handled                                                                                                                                                                                                                                                            |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `created_at` / `updated_at` columns | `seed_docs_demo` bulk-`update()`s them to fixed stamps, bypassing the auto fields                                                                                                                                                                                            |
| Row order across database rebuilds  | the same stamps must be **distinct** per row: `BaseModelViewSet.ordering = ["created_at"]` and `SmartOrderingFilter` appends `pk` as the pagination tiebreaker (`core/views.py:955`), and `pk` is a random UUID — so any tie on `created_at` shuffles lists on every rebuild |
| Random fixture content              | `seed_docs_demo` seeds the RNG and uses a fixed vocabulary — unlike the `populate_*` commands                                                                                                                                                                                |
| Animations, spinners, caret blink   | CSS injected before capture, plus `animations: 'disabled'`                                                                                                                                                                                                                   |
| Locale, timezone, colour scheme     | pinned to `en-GB` / `UTC` / `light` in the config                                                                                                                                                                                                                            |
| Viewport                            | 1440×900, re-declared _after_ the `devices[…]` spread, which carries its own viewport and would otherwise win                                                                                                                                                                |
| "Get Started" onboarding CTA        | `show_get_started` global setting turned off by the seed                                                                                                                                                                                                                     |

## Known caveats

- **Chart pages have drifted once, intermittently.** All 13 shots now reproduce
  byte-for-byte across two full database rebuilds, but an earlier pair of runs
  showed `audit-detail`'s ECharts donut differing by 114 px of 1,296,000
  (0.009%) with identical values and colours. It has not recurred. Treat chart
  shots with a small pixel threshold rather than a checksum until there is
  more evidence either way.
- The sticky breadcrumb bar can overlap a clipped card near the top of a page.
- Sidebar sections render collapsed; expand them in a `then` step if a shot
  needs a specific menu open.
- Requires the demo stack to be reachable; the harness has no `webServer` block
  so a failure is a stack failure, not a flaky test.
