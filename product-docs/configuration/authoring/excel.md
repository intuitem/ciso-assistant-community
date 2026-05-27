---
description: Authoring frameworks, matrices, and other library content from Excel
---

# Excel-driven authoring

> _Stub — to be expanded._

**Excel is the recommended authoring format** for most CISO Assistant content. Once an Excel file is written it gets converted to YAML by a single command, and the resulting `.yaml` is what the platform actually loads. The Excel route is faster than hand-writing YAML, much easier to review with non-engineers, and the converter tooling validates the structure for you before it ever reaches your instance.

This page captures the editorial conventions for Excel-driven authoring; the full v2 Excel format reference and the converter command-line are in [Designing your own libraries](../libraries/custom-libraries.md).

## What this page will cover

- **Why Excel over raw YAML** — fewer errors, easier diff with subject-matter experts, free spreadsheet validation (data types, dropdowns).
- **The v2 format at a glance** — `_meta` tab, per-object tabs (requirements, matrices, threats, reference controls, mappings), the `depth` / `assessable` columns.
- **Skeleton generation** — using `prepare_framework_v2.py` to scaffold a valid Excel file rather than starting from a blank sheet.
- **Conversion workflow** — `convert_library_v2.py my_file.xlsx`, where the YAML lands, how to spot validation errors.
- **What can be authored in Excel** — frameworks, risk matrices, threat catalogues, reference controls, mappings; what _can't_ (custom code, dynamic logic).
- **Reviewing in spreadsheet form** — using sheet review, comments, and named ranges to collaborate with non-engineers before conversion.
- **Excel pitfalls** — auto-formatting numbers as dates, hidden characters from PDF copy-paste, encoding mismatches in non-Latin scripts.

## Existing material

- [Designing your own libraries](../libraries/custom-libraries.md) — the full Excel-to-YAML reference, including the v2 format spec and the converter usage.
- [`tools/example_framework.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/example_framework.xlsx) — annotated reference Excel that converts cleanly.
- [`tools/excel/`](https://github.com/intuitem/ciso-assistant-community/tree/main/tools/excel) — repository of real Excel sources used to produce the built-in libraries (CIS, CCB, e-ITS, CMMC, …).

## Related

- [Framework authoring](framework.md) — the editorial discipline that sits on top of the Excel format.
- [Risk matrix authoring](matrix.md) — the matrix-specific conventions when authored in Excel.
- [Library upgrade](../libraries/library-upgrade.md) — what changes in a re-converted Excel file are safe to ship as a minor upgrade.
