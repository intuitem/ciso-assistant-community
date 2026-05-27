---
description: Guidelines for authoring a risk matrix that matches your enterprise risk language
---

# Risk matrix authoring

> _Stub — to be expanded._

A risk matrix in CISO Assistant declares the **probability scale**, the **impact scale**, and the **resulting risk levels** in their combination — the inputs every risk scenario reads from. Most organisations already have an internal risk taxonomy (often 5×5, sometimes 4×4 or 3×3) and want CISO Assistant to mirror it exactly rather than impose a new one. This page captures the design decisions that make a custom matrix land cleanly; the YAML format itself is documented in [Designing your own libraries](../libraries/custom-libraries.md).

## Matrix editor

The platform ships with an **in-app matrix editor** — a visual designer that lets you author a risk matrix directly in the UI, with live preview and real-time validation. This is the **recommended authoring pattern going forward**, especially for the many cases where a custom matrix only differs from a built-in one by axis wording, colour palette, or one or two cells.

You can reach it at **`/experimental/matrix-editor`** in your instance. It's currently exposed under the _experimental_ namespace while the UX is being polished — the menu entry and URL are likely to move once it graduates, but the underlying tool is the same.

### What it does

- **New from scratch** — _New matrix_ creates a sensible default 3×3 (Low / Medium / High) you can grow into 5×5 or trim down. Every change is captured in a **draft** that you save explicitly with _Save draft_; nothing reaches the live matrix list until you _Publish_.
- **Import from YAML** — load an existing library YAML directly into the editor (e.g. a community matrix you want to tune), without touching the file system.
- **Export as YAML** — once the matrix shape looks right, export the current draft as a library-ready YAML file you can ship as a custom library or version-control.
- **Edit your own matrices** — any matrix you authored on the instance is editable in place: _Edit_ creates an editable draft, and re-opening returns the same draft idempotently so you can leave and come back.
- **Fork a built-in or library matrix** — library-imported matrices show a **Clone** action that creates a fresh editable copy in your namespace; the original library matrix stays intact and remains upgradable.
- **Live preview** — every change re-renders the matrix the way analysts will see it (with legend), so you can validate colour, ordering, and cell mapping before publishing.
- **Real-time validation** — warnings surface inline for missing names, missing colours, duplicate abbreviations, grid/dimension mismatches, and invalid cell values, so you catch errors before they reach an audit.

### What you can edit inline

The editor is organised as four tabs and a metadata block, mirroring the structure of the YAML:

- **Probability** — the likelihood / frequency axis. Per level: abbreviation, name, description, colour. Add, remove, reorder; the grid is remapped automatically.
- **Impact** — the consequence axis. Same per-level controls as probability.
- **Risk levels** — the resulting risk classes (typically _Low / Medium / High / Very High / Critical_). Editing here updates the cell colour palette throughout.
- **Grid** — the `(probability × impact) → risk level` cell mapping, edited as a visual table. Cells are remapped automatically when you add or remove levels on either axis.
- **Metadata** — matrix name, description, and provider. Translatable for multi-language deployments (add target locales from the language switcher and edit name/description per level in each language).

### When to use the editor vs. Excel

- **Editor** — for matrices that live primarily on this instance (internal taxonomy, forked variants, in-progress drafts), and for matrices you intend to share as a library YAML afterwards (_Export as YAML_ produces a publishable file).
- **Excel** — when the matrix is part of a larger Excel workbook that also defines a framework, threats, or reference controls and you want a single conversion step. See [Excel-driven authoring](excel.md) and [Designing your own libraries](../libraries/custom-libraries.md).

The two paths are compatible: an Excel-built matrix can be imported into the editor (via _Import YAML_ after conversion) and tuned in place, and an editor-built matrix can be exported as YAML for redistribution.

## What this page will cover

- **Choosing the matrix size** — 3×3 vs. 4×4 vs. 5×5: trade-offs between granularity, analyst fatigue, and discriminating power on the residual axis.
- **Axis labels** — wording for probability levels (likelihood vs. frequency), wording for impact levels (qualitative vs. quantitative anchors).
- **Risk-level cells** — assigning each `(probability, impact)` cell to a risk level (typically _Low / Medium / High / Very High_); when to use a symmetric matrix vs. an impact-weighted one.
- **Colour coding** — palette accessibility, avoiding red/green-only encodings.
- **Tolerance lines** — drawing the threshold between acceptable and unacceptable risk, and how that drives the [risk acceptance](../../concepts/risk-assessments.md) workflow.
- **Localisation** — translatable labels and descriptions.
- **Versioning** — what changes can land in a v1.1 (typo fixes, label tweaks) vs. what requires a fresh matrix (rescaling, dimension change).

## Existing material

- [Risk matrices concept](../../concepts/risk-matrices.md) — what a risk matrix _is_ in the data model.
- [Designing your own libraries](../libraries/custom-libraries.md) — full Excel-to-YAML reference, including the matrix schema.
- `tools/custom_matrix_5x5.yaml` — annotated reference example shipped with the repository.

## Related

- [Framework authoring](framework.md) — frameworks often ship with a recommended matrix in the same library.
- [Risk assessments concept](../../concepts/risk-assessments.md) — how matrices are consumed at assessment time.
- [Contributing → Frameworks and libraries](../../contributing/framework.md) — how to upstream a community-shareable matrix.
