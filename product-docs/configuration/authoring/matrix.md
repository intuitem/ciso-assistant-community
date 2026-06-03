---
description: Task-oriented recipes for authoring a risk matrix — build, fork, translate, publish
---

# Risk matrix authoring

A risk matrix in CISO Assistant declares the **probability scale**, the **impact scale**, and the **resulting risk levels** in their combination — the inputs every risk scenario reads from. Most organisations already have an internal risk taxonomy (often 5×5, sometimes 4×4 or 3×3) and want CISO Assistant to mirror it exactly rather than impose a new one. The recommended way to author one is the **in-app matrix editor** at **`/experimental/matrix-editor`**. This page is a set of task-oriented recipes — find the one that matches what you're trying to do, follow the steps. For the complete walkthrough of every surface in the editor, see [Matrix editor — reference](matrix-editor.md).

{% hint style="warning" %}
**Experimental.** The matrix editor is exposed under the `/experimental/` namespace while its UX is being polished. The URL and menu entry are likely to move once it graduates, and individual surfaces may change between releases. The underlying data stays — your drafts and published matrices aren't at risk — but expect occasional rough edges. Feedback is welcome.
{% endhint %}

## Tasks

### Create a 5×5 matrix from scratch

The editor seeds new matrices as 3×3 by default. To get to a 5×5:

1. Go to **`/experimental/matrix-editor`** and click **New matrix**. A default 3×3 _Untitled_ matrix opens.
2. Fill in **Matrix name** (e.g. _"5×5 Cyber Risk Matrix"_) and an optional description at the top.
3. Open the **Probability** tab. Click **Add level** twice to get from 3 to 5 levels. For each level, set:
   - **Abbreviation** (e.g. `VL`, `L`, `M`, `H`, `VH`).
   - **Name** (e.g. _Very Low_, _Low_, _Medium_, _High_, _Very High_).
   - **Description** — the criteria (_"Less than once per 5 years"_, _"More than 10 per year"_, etc.).
4. Switch to the **Impact** tab and do the same — add 2 more levels and set abbreviations, names, descriptions.
5. Switch to the **Risk levels** tab. Adjust the level count (4 is the default; tick **Add level** for a 5th tier or **Delete** for fewer). Set the name, description, and colour of each.
6. Switch to the **Grid** tab. Click each cell to cycle through risk levels until the heatmap matches your desired severity zoning. Use the hover dropdown for direct selection.
7. Scroll down to the **Matrix preview** card. Verify the rendering looks right.
8. Click **Save draft**, then **Publish matrix** when ready. Confirm the publish dialog.

### Fork (clone) a library matrix and adapt it

To start from a built-in or library matrix rather than the default:

1. Open **`/experimental/matrix-editor`**.
2. Find the matrix you want to fork in the list (it'll have a **From library** badge).
3. Click **Clone** in its row. A new editable matrix is created, seeded with the source's content as a draft. The source matrix stays untouched.
4. Edit the clone — rename, retune levels, recolour, adjust the grid. The clone has no library backing, so it won't be touched by future library upgrades.
5. **Save draft** and **Publish** when ready.

### Import a YAML matrix

If you have a matrix in library YAML format (from an Excel conversion, source control, or a colleague):

1. Open **`/experimental/matrix-editor`** and click **Import YAML**.
2. Pick the YAML file in the file picker. The platform parses it server-side and creates a new draft on the instance.
3. The imported matrix opens automatically — name, description, all four object lists, and translations all loaded.
4. Edit further if needed and **Publish** when ready.

### Add or remove a level

A level is a row in any of the Probability / Impact / Risk levels tabs.

#### Add

1. Switch to the right tab.
2. Click **Add level** above the table. A new level appears at the bottom with a default abbreviation, an empty name and description, and a palette colour matching the current scheme.
3. Fill in **Abbreviation**, **Name**, **Description**. The colour picker on the right lets you tweak the hex if you want to override the palette.

#### Remove

1. Switch to the right tab.
2. Click the **Delete** (trash) button on the level's row. The button is disabled if only 2 levels remain (the editor enforces a minimum).
3. The grid remaps automatically — moving a probability level drops the corresponding row; deleting a risk level falls back to the first risk level on any cell that pointed at it (the validation panel flags any side effects).

> Important: deleting a risk level used by cells in the grid is the most fragile operation in the editor. Check the **Validation warnings** panel after deleting to confirm no cells ended up out of range.

### Edit the grid (set cell risk levels)

The grid maps every `(probability, impact)` pair to a risk level. Two ways to edit:

#### Click to cycle

1. Open the **Grid** tab.
2. Click any cell. The cell cycles to the next risk level (Low → Medium → High → Critical → Low). Keep clicking to land on the level you want.

#### Hover to pick

1. Hover any cell. A dropdown appears listing every risk level by colour and name.
2. Click the level you want. The cell updates immediately.

> The dropdown flips upward for cells in the bottom half of the grid so it doesn't fall off the page.

You can also focus a cell and press `Enter` or `Space` to cycle (same as clicking).

### Apply a colour palette

For consistent, accessible colour schemes across all three level tabs:

1. Open any of the **Probability**, **Impact**, or **Risk levels** tabs.
2. At the top of the table, click one of the four palette previews:
   - **Classic** — green → red progression. The default.
   - **Accessible** — Wong's colourblind-safe palette (blue / sky / yellow / orange / vermillion / pink / green / black).
   - **Warm** — cream-to-burgundy progression.
   - **Cool** — light-cyan-to-deep-teal progression.
3. Every level on that tab gets its colour rewritten in order. Custom hex colours you set previously are overwritten — re-apply per level if you want to tweak.
4. Repeat for the other two tabs to keep all three coherent.

### Translate to another language

1. Open the matrix in the editor.
2. In the **Languages** strip above the editor, open the **Add language** dropdown and pick the target locale (e.g. _French_). It's added as a translation chip.
3. Click the new language chip to switch the editor into translation mode.
4. Walk through all four tabs. Every translatable field (name, description on each level; name + description on the matrix metadata) splits into a base column (read-only) and a translation column (editable). The base value shows as a placeholder when the translation is empty.
5. Translate metadata at the top of the editor too — the matrix name and description carry their own translations.
6. **Save draft** and **Publish** when ready.

> To remove a translation entirely, click the `×` on the language chip. A confirmation prompt asks before dropping every translation for that language.

### Publish your draft

1. Make sure the **Validation warnings** panel (above the live preview) is clean. The publish is blocked while any warning is unresolved.
2. Save the draft first if it's dirty.
3. Click **Publish matrix** in the toolbar. A confirmation dialog appears.
4. Click **OK** to confirm. The matrix flips to published — every risk scenario referencing it picks up the new shape on next refresh.

> Publishing immediately affects every risk scenario that uses this matrix. Current and residual risk levels are recomputed against the new grid the next time a scenario is opened. If a change turns out to be wrong, use **Discard draft** + re-edit before the next risk-review cycle.

### Discard a draft

To throw away in-progress edits and start over from the live state:

1. Find the matrix in the list. If it's a published matrix with an active draft, the **Discard draft** button appears in the row's actions.
2. Click it. The server-side draft is deleted and a fresh draft is re-created from the live state.
3. If the matrix has never been published, the action is **Delete** instead — it removes the whole matrix.

### Export as a YAML library

To take a matrix out of this instance — for source control, sharing with another instance, or shipping to the community catalogue:

1. Open the matrix in the editor. Make sure any unsaved edits are saved (export auto-saves, but the export reflects what's _live_ ideally).
2. Click **Export YAML** in the toolbar. The browser downloads a library-format YAML file with metadata, all four object lists, hex colours, translations, and the matrix URN.
3. The file is ready to load on another instance via the [Libraries](../libraries/README.md) section.

## Editorial discipline

The editor will let you build almost any matrix shape, but the matrices that actually work for analysts are narrower. A few principles:

### Choose the right size

- **3×3** — the smallest matrix worth building. Suits early-stage programmes where consistent assessment matters more than fine-grained discrimination. 4 risk levels (Low / Medium / High / Critical) work well at 3×3.
- **4×4** — the in-between size. Often used by organisations that found 3×3 too blunt and 5×5 too analyst-fatiguing. 4–5 risk levels.
- **5×5** — the industry standard for mature programmes (ISO 27005, ANSSI EBIOS RM, NIST). 5 levels per axis × 5 risk classes is the canonical fit. Beyond 5×5, discrimination doesn't actually improve — and the residual-vs-current axis becomes hard to read.
- **3×5 / 5×3** — asymmetric matrices are rare but valid (e.g. fewer probability classes for binary-ish threats). The editor supports them.

### Axis wording

- **Probability vs frequency vs likelihood** — pick one and stick to it. _Likelihood_ is the safest for general risk; _frequency_ reads better for operational risk; _probability_ is more formal and pairs well with quantitative methods.
- **Anchor each level with a number where you can.** _"More than 1 per year"_ is testable; _"Frequent"_ isn't. The description field is where these anchors live.
- **Impact wording should mirror your business.** Don't use generic _Minor / Major_ if the organisation has an internal grading (_Operational / Tactical / Strategic_).

### Colour and palette

- **Use the accessible palette by default.** Red / green confusion is the single most common colour-vision issue; the _Accessible_ palette (Wong's set) avoids it without losing perceptual ordering.
- **Don't override individual colours unless you have a reason.** Custom hex per level reads as inconsistency; a clean palette reads as polish.
- **Risk-level colours signal severity** — keep them monotonic (green → yellow → orange → red, not green → red → orange → yellow). The default palettes already do this.

### Tolerance and the grid shape

- **Symmetric matrices** (cell `(i, j)` and `(j, i)` get the same risk) are the default for organisations that weigh probability and impact equally.
- **Impact-weighted matrices** (cells where impact > i are bumped up) suit organisations that treat catastrophic-impact events as never-acceptable.
- **The "tolerance line"** — the boundary between acceptable and unacceptable risk — is implicit in the grid colouring. Make it visually clear. If _Low_ and _Medium_ are both "acceptable" but _High_ isn't, give them adjacent green-ish hues and switch to red at _High_.

### Versioning

Once a matrix is published and risk scenarios reference it, **changes ripple immediately**:

- Renaming a level — safe, label-only.
- Re-colouring a level — safe, presentation-only.
- Adding a level — safe, additive (existing scenarios keep their assignments).
- **Removing a level** — risky. Scenarios pointing at the removed level get clamped to a fallback; this is what the validation panel warns about. Prefer _Discard draft_ and _Clone_ to a new matrix over destructive level removal on a matrix in use.
- **Changing a cell value** — safe, but every scenario whose `(probability, impact)` pair sits in that cell will see a different risk level the next time it's evaluated. Verify with the preview before publishing.

### Localisation

- **Author in the base language first.** Don't start translating before the base is settled — every level rename rewrites the translation hint.
- **Mind the abbreviation column.** Abbreviations don't get translated (they're identifiers, not labels). A French matrix can have `name: "Faible"` and `abbreviation: "L"`, or `abbreviation: "F"` — both work, just stay consistent.

## When to use the editor vs. Excel

- **Editor** — for matrices that live primarily on this instance (internal taxonomy, forked variants, in-progress drafts), and for matrices you intend to share as a library YAML afterwards (_Export as YAML_ produces a publishable file). The editor wins everywhere translations and palette tuning are part of the work.
- **Excel** — when the matrix is part of a larger Excel workbook that also defines a framework, threats, or reference controls and you want a single conversion step. See [Excel-driven authoring](excel.md) and [Designing your own libraries](../libraries/custom-libraries.md).

The two paths are compatible: an Excel-built matrix can be imported into the editor (via _Import YAML_ after conversion) and tuned in place, and an editor-built matrix can be exported as YAML for redistribution.

## Related

- [Matrix editor — reference](matrix-editor.md) — every surface and action in the editor.
- [Risk matrices concept](../../concepts/risk-matrices.md) — what a risk matrix _is_ in the data model.
- [Framework authoring](framework.md) — frameworks often ship with a recommended matrix in the same library.
- [Risk assessments concept](../../concepts/risk-assessments.md) — how matrices are consumed at assessment time.
- [Excel-driven authoring](excel.md) — when to fall back to spreadsheets.
- [`tools/custom_matrix_5x5.yaml`](https://github.com/intuitem/ciso-assistant-community/blob/main/tools/custom_matrix_5x5.yaml) — annotated reference example shipped with the repository.
- [Contributing → Frameworks and libraries](../../contributing/framework.md) — how to upstream a community-shareable matrix.
