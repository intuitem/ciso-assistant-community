---
description: Guidelines for authoring frameworks, risk matrices, journey presets, and Excel-driven content
---

# Authoring

This section gathers the **authoring guidelines** — the conventions, structure, and pitfalls to keep in mind when you create the content that drives CISO Assistant: frameworks, risk matrices, journey presets, and Excel-driven library content.

Authoring is a separate discipline from running the platform. Once content has been authored, it's loaded through the [Libraries](../libraries/README.md) section and behaves the same as any built-in content — versioned, upgradable, exportable. The pages here focus on _writing the content_, not on loading it.

For frameworks, matrices, and presets, the **recommended path is the in-app visual editor** — they all ship with a dedicated builder under the `/experimental/` namespace, complete with draft/publish lifecycle, live preview, real-time validation, and multi-language support. Each guide walks through its builder in depth before covering editorial discipline. Excel-driven authoring remains the right channel for library publishing across instances.

## What's in this section

- [Framework authoring](framework.md) — how to design a requirement tree, name nodes, use implementation groups, attach scoring scales and questions, and pick reference controls / threats.
- [Risk matrix authoring](matrix.md) — choosing dimensions, colour coding, axis labels, and the trade-offs between 3×3, 4×4, and 5×5 layouts.
- [Journey preset authoring](preset.md) — designing reusable templates of audits, risk assessments, and supporting objects intended to be reused across teams.
- [Excel-driven authoring](excel.md) — the recommended workflow for authoring frameworks, matrices, and other library content from Excel before conversion to YAML.

## When to read this section

- You're building your own framework (industry-specific, internal policy, regulatory adaptation) and want to do it right the first time.
- You're **forking an existing framework** as a baseline — copying a built-in or community library, then tuning it to your context (renaming the URN, pruning, adding in-house requirements) rather than starting from a blank page.
- You're modelling a custom risk matrix that needs to match your enterprise's existing risk taxonomy.
- You're standardising a journey preset for a recurring assessment pattern (yearly ISO audit, supplier onboarding, new project intake).
- You want to understand the editorial rules behind the platform's built-in content before contributing or forking it.

## Related

- [Libraries](../libraries/README.md) — how to load, upgrade, and clean up authored content.
- [Designing your own libraries](../libraries/custom-libraries.md) — the full Excel-to-YAML workflow that backs framework and matrix authoring.
- [Contributing → Frameworks and libraries](../../contributing/framework.md) — how to upstream authored content to the community library.
