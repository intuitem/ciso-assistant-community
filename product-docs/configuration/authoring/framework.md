---
description: Guidelines for designing a framework so it lands cleanly in CISO Assistant
---

# Framework authoring

> _Stub — to be expanded._

A framework in CISO Assistant is a tree of **requirement nodes** that gets imported from a YAML library file. Authoring one well is more than translating a PDF into rows: the structure you pick drives how analysts navigate, how progress rolls up, and how the framework maps to others. This page captures the editorial discipline; the YAML format itself is documented in [Designing your own libraries](../libraries/custom-libraries.md).

## What this page will cover

- **Requirement tree shape** — when to use depth vs. breadth, how titles vs. assessable nodes work, the cost of over-nesting.
- **Naming and IDs** — URN conventions, stable identifiers across versions, sortable codes (`01.01`, `01.02`).
- **Implementation groups** — when to introduce them, maturity tiers vs. scoping slices (see the [Implementation groups](../../concepts/audits.md#implementation-groups) discussion in audits).
- **Scoring scales** — picking a maturity scale, defining level descriptions, when to enable the documentation-score layer.
- **Questions** — using the questionnaire layer to make a framework actionable for non-experts.
- **Reference controls and threats** — what to bundle in the same library vs. depend on from another.
- **Mappings** — designing a framework so it maps cleanly to ISO 27001 / NIST CSF / etc.
- **Localisation** — translatable fields, RTL considerations, the `translations` block.

## Existing material

- [Designing your own libraries](../libraries/custom-libraries.md) — full Excel-to-YAML reference, including the framework schema.
- [Getting your custom framework](../libraries/custom-frameworks.md) — quick-start for a single-framework library.
- [Frameworks concept](../../concepts/frameworks.md) — what a framework _is_ in the data model.
- [Multi-level support](../../features/multi-level-support.md) — how implementation groups are selected at audit creation.

## Related

- [Risk matrix authoring](matrix.md) — the other half of most security libraries.
- [Library upgrade](../libraries/library-upgrade.md) — what changes are safe to ship in a v1.1 of a framework you've authored.
- [Contributing → Frameworks and libraries](../../contributing/framework.md) — how to upstream a framework to the community catalogue.
