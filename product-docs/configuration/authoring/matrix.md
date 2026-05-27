---
description: Guidelines for authoring a risk matrix that matches your enterprise risk language
---

# Risk matrix authoring

> _Stub — to be expanded._

A risk matrix in CISO Assistant declares the **probability scale**, the **impact scale**, and the **resulting risk levels** in their combination — the inputs every risk scenario reads from. Most organisations already have an internal risk taxonomy (often 5×5, sometimes 4×4 or 3×3) and want CISO Assistant to mirror it exactly rather than impose a new one. This page captures the design decisions that make a custom matrix land cleanly; the YAML format itself is documented in [Designing your own libraries](../libraries/custom-libraries.md).

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
