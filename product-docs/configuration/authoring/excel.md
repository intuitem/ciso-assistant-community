---
description: Authoring frameworks, matrices, and other library content from Excel
---

# Excel-driven authoring

> _Stub — to be expanded._

Excel is one way to author library content, especially when adapting a source spreadsheet or preparing a file to share. CISO Assistant accepts the workbook directly and converts it to YAML during import. To create and edit a library on your instance without a spreadsheet, use the [Library builder](library-builder.md).

This page introduces Excel-driven authoring. For the workbook creation and optional conversion steps, see [Create a Library](../libraries/create-library.md). The [Library objects](../libraries/library-objects/README.md) pages describe the sheets and fields for each object.

For framework scoring, the framework `_meta` tab defines the default `min_score`, `max_score`, and `scores_definition` used when audits are created. Individual requirement rows can override those values with their own `min_score`, `max_score`, and `scores_definition_ref` (a named entry in the framework's `scores_definition.alternatives` registry) when a framework mixes scoring ranges. Leave those cells blank to inherit the audit-level scale at runtime.

## What this page will cover

- **Why Excel over raw YAML** — fewer errors, easier diff with subject-matter experts, free spreadsheet validation (data types, dropdowns).
- **The v2 format at a glance** — `_meta` tab, per-object tabs (requirements, matrices, threats, reference controls, mappings), the `depth` / `assessable` columns.
- **Skeleton generation** — using `prepare_framework_v2.py` to scaffold a valid Excel file rather than starting from a blank sheet.
- **Conversion workflow** — `convert_library_v2.py my_file.xlsx`, where the YAML lands, how to spot validation errors.
- **What can be authored in Excel** — frameworks, risk matrices, threat catalogues, reference controls, mappings; what _can't_ (custom code, dynamic logic).
- **Reviewing in spreadsheet form** — using sheet review, comments, and named ranges to collaborate with non-engineers before conversion.
- **Excel pitfalls** — auto-formatting numbers as dates, hidden characters from PDF copy-paste, encoding mismatches in non-Latin scripts.

## Existing material

- [Create a Library](../libraries/create-library.md) — the step-by-step Excel workflow and optional YAML conversion.
- [`tools/example_framework.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/example_framework.xlsx) — annotated reference Excel that converts cleanly.
- [`tools/excel/`](https://github.com/intuitem/ciso-assistant-community/tree/main/tools/excel) — repository of real Excel sources used to produce the built-in libraries (CIS, CCB, e-ITS, CMMC, …).

## Related

- [Library builder](library-builder.md) — the in-app alternative, and the editorial discipline that sits on top of the library format.
- [Update a library](../libraries/update-library.md) — how to publish a new version and apply it to existing audits.
