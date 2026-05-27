---
description: Guidelines for designing a framework so it lands cleanly in CISO Assistant
---

# Framework authoring

> _Stub — to be expanded._

A framework in CISO Assistant is a tree of **requirement nodes** that gets imported from a YAML library file. Authoring one well is more than translating a PDF into rows: the structure you pick drives how analysts navigate, how progress rolls up, and how the framework maps to others. This page captures the editorial discipline; the YAML format itself is documented in [Designing your own libraries](../libraries/custom-libraries.md).

You don't have to start from a blank page. A common pattern is to **fork an existing framework** — take a built-in one (or any community-shared library) as a baseline, then copy and tune it: rename the URN to your own namespace, prune the requirements you don't need, add organisation-specific ones, adjust the scoring scale, and ship it as a new library. This is the fastest route for industry-specific adaptations (an ISO 27001 variant for a regulated sector), internal policy frameworks that should align with NIST CSF, or regulatory frameworks that need extra in-house requirements layered on top. Forking keeps the editorial work focused on the _delta_ you actually care about, while inheriting the structure and conventions of a library that has already been battle-tested across audits.

## Framework builder

The platform now ships with an **in-app framework builder** — a visual editor that lets you design a framework directly in the UI instead of (or alongside) the Excel + YAML round-trip. This is the **recommended authoring pattern going forward**: most of the structural decisions covered on this page can be expressed live in the builder, with real-time validation and a preview of how the framework will render to analysts.

You can reach it at **`/experimental/framework-builder`** in your instance. It's currently exposed under the _experimental_ namespace while the UX is being polished — the menu entry and URL are likely to move once it graduates, but the underlying tool is the same.

### What it does

- **New from scratch** — _New Framework_ creates an empty, editable framework in your root domain and opens the editor.
- **Edit your own frameworks** — any framework you authored is editable directly: open it in the builder and a **draft** is created on the fly. Drafts are idempotent (re-opening returns the existing draft), so you can leave and come back without losing work. The frameworks list highlights _Frameworks with Active Drafts_ at the top so you can resume.
- **Fork a built-in library** — frameworks imported from a library are locked in the editor and surface a **Create a copy and edit** button. The clone lands as a fully editable framework in your namespace, ready to tune; the original library stays intact and remains upgradable.
- **Preview** — a dedicated preview view renders the framework the way an analyst will see it during an audit, so you can validate the navigation flow before publishing.

### What you can edit inline

The builder exposes editors for every structural piece a framework carries:

- **Requirement tree** — add titled section nodes and assessable requirements, reorder, indent (depth changes), delete.
- **Implementation groups** — define the IG taxonomy (maturity tiers or scope slices) and assign each requirement to one or more groups.
- **Questions and choice lists** — attach the questionnaire layer used by [flash mode](../../features/flash-mode.md) and respondent flows.
- **Dependencies (`depends_on`)** — model conditional requirements that only apply when a parent is answered a certain way.
- **Outcomes / scoring hints** — describe the maturity levels that the scoring scale will use.
- **Keyboard navigation** — the builder is keyboard-first; press `?` inside the editor for the full shortcut sheet.

### When to use the builder vs. Excel

- **Builder** — for frameworks that live primarily on this instance (internal policies, forked variants, in-progress drafts), and for any iterative editing where the round-trip cost of Excel-to-YAML conversion is too high.
- **Excel** — for frameworks you intend to ship as a library file (community catalogue, multi-instance deployments, version-controlled releases). See [Excel-driven authoring](excel.md) and [Designing your own libraries](../libraries/custom-libraries.md).

The two paths are not mutually exclusive: a framework you built in Excel can be loaded as a library, forked through the builder, and tuned in place; conversely, a framework drafted in the builder can be exported (in due course) to YAML for redistribution.

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
