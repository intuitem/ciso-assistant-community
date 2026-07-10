---
description: Complete reference for the in-app risk matrix editor — every surface, every action, every nuance
---

# Matrix editor — reference

This page is the **complete reference** for the in-app matrix editor. It covers every surface, every action, and every nuance. If you're looking for step-by-step recipes (_"how do I create a 5×5 matrix?"_, _"how do I translate one to French?"_), start with [Risk matrix authoring](matrix.md) — this page is the lookup material the recipes link into.

The editor lives at **`/experimental/matrix-editor`**.

{% hint style="warning" %}
**Experimental.** The matrix editor is exposed under the `/experimental/` namespace while its UX is being polished. The URL and menu entry are likely to move once it graduates, and individual surfaces may change between releases. The underlying data stays — your drafts and published matrices aren't at risk — but expect occasional rough edges. Feedback is welcome.
{% endhint %}

## Opening the editor

The editor is single-page: list, editor, and live preview on the same screen. On first load, if any matrix has an active draft, the most recently updated one auto-opens — so resuming editing is one navigation away, not a click-through-to-find. The page is organised as:

1. **Top toolbar** — _New matrix_, _Import YAML_, _Export YAML_, status pill, _Save draft_, _Publish_.
2. **Matrix list** — every matrix on the instance, with drafts at the top.
3. **Language switcher and metadata block** — only visible when a matrix is open.
4. **Editor tabs** — Probability, Impact, Risk levels, Grid.
5. **Validation warnings panel** — only shown when warnings exist.
6. **Live preview** — the matrix rendered the way analysts see it on a risk scenario.

## The matrix list

Two row types share a single table, with column headers _Name / Description / Status / Locale / Actions_:

- **Drafts** (top, highlighted) — matrices with an active editing draft. Each row carries a status pill: **Published** (green) if the live matrix exists too, **New** (amber) if the draft has never been published, and an _Editing_ badge to mark the draft. The action column shows **Continue editing** (or **Close** when you're already in it) and either **Discard draft** (for published matrices — reverts to the live state) or **Delete** (for unpublished — deletes the whole matrix).
- **Published matrices without drafts** — the rest of the matrices on the instance. They carry **Published** status, an optional **From library** badge for matrices that came from a YAML library, and a version suffix (`v{n}`) when the matrix has been published more than once. The actions are **Edit** (only for matrices you authored on this instance — not for library-backed ones, which are read-only) and **Clone** (everyone — creates a fresh draft seeded from this matrix's content).

The **Locale** column shows every language the matrix has content in (base + targets); each locale gets its own chip so multi-language matrices are easy to spot.

### Editing a library-backed matrix

Library matrices are intentionally read-only — they ship from a YAML library and stay upgradable. The **Edit** action isn't offered; **Clone** is the path:

- Clone creates a brand-new matrix in your namespace, with its content copied from the library matrix as the starting draft.
- The clone has no library backing, so it's free to evolve and won't be touched by future library upgrades of the source.
- The original library matrix stays intact in the list, untouched.

This is the canonical fork-and-tune flow for adapting a published matrix to your organisation.

## Creating a matrix

Three entry points:

### New matrix

The **New matrix** button seeds a sensible default 3×3 matrix:

- 3 probability levels (_Low / Medium / High_).
- 3 impact levels (_Low / Medium / High_).
- 4 risk levels (_Low / Medium / High / Critical_), with a green-yellow-orange-red default palette.
- A 3×3 grid mapping `(probability, impact) → risk level` that already follows a sensible diagonal (mostly low at the bottom-left, mostly critical at the top-right).

The matrix is saved on the server immediately as a draft, so it shows up in the list right away.

### Import YAML

The **Import YAML** button opens a file picker for a library-format YAML matrix:

- The file is parsed server-side and turned into a new draft on the instance.
- All four pieces (probability, impact, risk levels, grid) and metadata (name, description, locale, translations) load directly into the editor.
- This is the right tool when you have an Excel-built matrix to bring in, or a community-shared YAML you want to tune in place.

### Clone

From any matrix row, **Clone** creates a fresh draft seeded from the cloned matrix's `json_definition`. The clone is yours; the source is untouched. This is the workflow for forking a library matrix (see above) and for spinning off a variant of one of your own matrices (_5×5 standard_ → _5×5 simplified_ for SaaS suppliers, etc.).

## The toolbar at a glance

- **New matrix** — seed a default 3×3 and start editing.
- **Import YAML** — load a library-format YAML.
- **Export YAML** — only available when a matrix is open. Exports the current state (auto-saves the draft first) as a library-ready YAML file. Filename comes from the server.
- **Status pill** — visible after the first save, mirrors the toast messages briefly (_Draft saved_, _Matrix published_, etc.) before fading.
- **Save draft** — persists the in-memory state to the server's `editing_draft`. The matrix is _not_ live yet — it's saved as a draft.
- **Publish matrix** — promotes the draft to the live definition. A confirmation dialog runs first; on success the matrix is what risk scenarios will pick up.

A **beforeunload** guard prevents accidental tab close or refresh when there are unsaved local edits — the browser asks for confirmation before navigating away.

## Metadata block

When a matrix is open, the editor header carries:

- **Matrix name** — the human-readable label. Required (the validation panel flags an empty name).
- **Description** — short note about the matrix (e.g. _"5×5 cybersecurity risk matrix, ANSSI-style"_).

Both fields are translatable — switching the language selector shows a translatable copy alongside the base content, with the base value shown as a hint below the translation input so you have context while translating.

## Languages

A dedicated language strip sits above the editor:

- **Base language** (left pill) — the matrix's primary locale. Click any other locale chip to switch the editor into translation mode.
- **Translation chips** — every additional language the matrix has content in. The active one is highlighted; click another to switch.
- **Remove language** — the small `×` on a translation chip removes that translation entirely (with confirmation). The base language can't be removed.
- **Add language** — a dropdown listing every locale not yet on the matrix. Picking one adds it as a translation target and switches the editor to it.
- **Default locale** — when more than one language exists, a separate dropdown lets you change which is treated as the base. Changing the base re-promotes the previously-translation content into the base slot.

In translation mode, every level editor splits each field into a base column (read-only) and a translation column (editable), with the base value as a placeholder hint. The matrix metadata behaves the same way. Switching back to the base language returns the editor to normal single-column editing.

## Editor tabs

The editor body is organised as four tabs, mirroring the YAML schema:

- **Probability** — the likelihood / frequency axis.
- **Impact** — the consequence axis.
- **Risk levels** — the resulting risk classes (Low / Medium / High / etc.).
- **Grid** — the `(probability, impact) → risk level` cell mapping.

### LevelEditor (Probability, Impact, Risk levels)

The three level tabs share the same editor. Each row in the table is one level, with these columns:

- **`#`** — the level's index, rendered as a coloured pill (uses the level's own hex colour). Read-only.
- **Abbreviation** — the short code (e.g. `1`, `L`, `Med`). Used in compact UI rendering.
- **Name** — the level's display label (e.g. _Low_, _Likely_, _Significant_). Translatable.
- **Description** — the level's criteria (e.g. _"Less than 1 occurrence per 5 years"_). Translatable.
- **Hex colour** — a colour picker. Drives the cell colour in the grid and the level chip everywhere it's shown.
- **Actions** — _Move up_, _Move down_, _Delete_. Minimum two levels per dimension; the delete button disables when only two remain.

Above the table, a **colour palette** picker lets you apply a preset palette to every level in one click:

- **Classic** — green / lime / yellow / amber / red / dark red — the default.
- **Accessible** — Wong's colourblind-safe palette (blue / sky / yellow / orange / vermillion / pink / green / black).
- **Warm** — cream-to-burgundy progression.
- **Cool** — light-cyan-to-deep-teal progression.

Applying a palette rewrites the hex colours on every level in order, so a 5-level scale gets the first 5 palette entries. The picker is purely a convenience — you can still hand-set individual colours afterwards.

#### Adding a level

The **Add level** button appends a new level with:

- Auto-incremented index.
- Default abbreviation (the index + 1).
- Empty name and description (you fill them in).
- A palette colour matching the current scheme.

#### Reordering and deleting

Moves and deletes don't just edit the level list — they **remap the grid** to keep it consistent:

- Moving a probability level swaps the corresponding grid rows.
- Moving an impact level swaps the corresponding grid columns.
- Moving a risk level remaps every grid cell that pointed at that risk level.
- Deleting a probability or impact level drops the corresponding row/column.
- Deleting a risk level remaps cells that pointed at it to the first risk level (the safe fallback); the editor flags this with a validation warning if any cell ended up out of range.

This is the most fragile part of authoring — adding and reordering are cheap, but deleting a risk level mid-flight is destructive. The editor lets you do it, but the validation panel surfaces the consequences inline so you can spot them.

### GridEditor

The grid tab renders the `(probability × impact)` matrix as a visual table:

- **Probability rows** run **top-to-bottom in descending order** (highest probability at the top) — this matches the heatmap convention used in the live RiskMatrix component, so the editor preview is unambiguous.
- **Impact columns** run **left-to-right** in level order.
- Each axis header carries its own coloured chip (using the level's hex colour and its abbreviation + name), so the dimensions are visible without consulting the level tabs.
- Each cell is coloured by the risk level it maps to, with the risk level's abbreviation centred in the cell.

Cells are interactive:

- **Click** a cell to cycle through the risk levels in order (Low → Medium → High → Critical → Low).
- **Hover** a cell to reveal a small dropdown listing every risk level by colour and name — click any entry to set the cell directly without cycling. The dropdown flips upward for cells in the bottom half of the grid, so it doesn't fall off the page.
- **Keyboard** — focus a cell and press `Enter` or `Space` to cycle (same as clicking).

The grid stays in sync with the level tabs automatically — adding a probability level adds a row, removing an impact level removes a column, etc. The validation panel flags any structural mismatch (rows ≠ probability levels, cols ≠ impact levels) and out-of-range cell values.

## Live preview

Below the editor, the **Matrix preview** card renders the matrix using the live **RiskMatrix** component — the same one analysts see on a risk scenario. The preview:

- Updates instantly on every change (level rename, colour tweak, cell click).
- Includes the legend, so you can verify the legend rendering before publishing.
- Hides itself when the matrix is incomplete (under 2 levels per dimension), with an inline message — _"Invalid matrix — need at least 2 levels per dimension"_.

The preview is the final fidelity check: scroll down, look at it, then publish.

## Real-time validation

A yellow **validation warnings** panel surfaces inline as you edit. It checks:

- **Dimensions** — each of probability, impact, and risk levels must have ≥ 2 entries.
- **Grid shape** — number of rows = number of probability levels; number of columns = number of impact levels.
- **Cell values** — every grid cell's value must be a valid risk level index (0 to max).
- **Required fields** — every level needs a name and a hex colour.
- **Duplicate abbreviations** — within a single dimension, abbreviations should be unique (the cell badge looks confusing otherwise).
- **Matrix name** — must not be empty.

Warnings are non-blocking — you can keep editing and save drafts with warnings present — but **publishing is blocked** until the matrix is valid. The panel surfaces every warning with enough context (which level, which cell, what value) to fix without hunting.

## The draft → publish lifecycle

The matrix editor uses a server-side **editing draft** that's distinct from the live matrix definition (`json_definition`):

1. **Create or open** — opening a matrix in the editor either starts a fresh draft from the live state (`start-editing` action) or loads the existing one. Drafts are idempotent: re-opening returns the same draft.
2. **Save draft** — explicitly via the **Save draft** button. Persists `editing_draft` on the server. The matrix is _not_ visible to risk scenarios yet.
3. **Publish** — promotes `editing_draft` into `json_definition`, bumping the matrix's `editing_version`. Risk scenarios immediately read the new shape. A confirmation dialog runs first; on success the toast confirms _Matrix published_.
4. **Discard draft** — for matrices that have a live `json_definition`, this throws the draft away and re-creates a fresh one from live. The button is in the matrix list, not the toolbar — _Discard draft_ on a published matrix; _Delete_ on an unpublished one (because there's no live to revert to).
5. **Switch away** — switching to a different matrix in the list with unsaved changes prompts a confirmation. The server-side draft is preserved either way; only in-memory edits get lost.

Publishing immediately affects every risk scenario referencing this matrix — current and residual risk levels are recomputed against the new grid the next time the scenario is opened or rolled up. This is why the editor's discard path matters: it's the safe revert when a session of edits turns out to be wrong.

## Exporting to YAML

The **Export YAML** button auto-saves the current draft, then downloads it as a library-format YAML file with:

- Metadata (`name`, `description`, `locale`, `provider`).
- All four object lists (probability, impact, risk, grid) including hex colours and translations.
- The matrix's URN.

The exported file is ready to ship to other CISO Assistant instances, to source control, or to a community library catalogue.

## What the editor doesn't do (yet)

- **Bulk matrix import from a workbook** — the import is one matrix at a time. Bringing in several matrices in one shot is still an Excel-to-YAML conversion job.
- **Symmetry helpers** — the editor doesn't have a "mirror to diagonal" or "auto-fill upper triangle" button. You set each cell explicitly. For most matrices this is fine; for large ones, the click-to-cycle pattern is faster than it sounds.
- **Side-by-side comparison with another matrix** — useful for diffing a custom matrix against a built-in one, but not yet exposed. The preview + a second tab is the workaround.

For these, fall back to [Designing your own libraries](../libraries/custom-libraries.md) or [Excel-driven authoring](excel.md).

## Related

- [Risk matrix authoring](matrix.md) — the task-oriented entry point that links into this reference.
- [Risk matrices concept](../../concepts/risk-matrices.md) — what a risk matrix _is_ in the data model.
- [Framework authoring](framework.md) — frameworks often ship with a recommended matrix in the same library.
- [Excel-driven authoring](excel.md) — when to fall back to spreadsheets.
- [Designing your own libraries](../libraries/custom-libraries.md) — the full Excel-to-YAML reference, including the matrix schema.
