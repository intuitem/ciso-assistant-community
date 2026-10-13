---
name: cis-benchmark-framework
description: Convert a CIS Benchmark PDF into a CISO Assistant framework library (YAML) by extracting only the "Appendix: Summary Table" — recommendation numbers, titles, and their Automated/Manual tag as implementation groups. Stays within the same IP boundary as the existing cis-benchmark-kubernetes library (no audit/remediation/rationale content). Use when the user asks to "convert a CIS benchmark PDF to a framework", "add the CIS <tech> Benchmark as a library", or drops new benchmark PDFs (e.g. in cis_benchmarks/) to be turned into CISO Assistant frameworks.
---

# CIS Benchmark PDF → CISO Assistant framework

## What this skill does

Two-step reproducible pipeline, run from the repo root:

```bash
# 1. PDF → v2 Excel (5 sheets, same shape as tools/excel/cis/cis-benchmark-kubernetes.xlsx)
.venv/bin/python .claude/skills/cis-benchmark-framework/scripts/extract_cis_benchmark.py \
    path/to/CIS_<Tech>_Benchmark_vX.Y.Z.pdf \
    --ref-id cis-benchmark-<tech> \
    --name "CIS <Tech> Benchmark" \
    -o tools/excel/cis/cis-benchmark-<tech>.xlsx

# 2. Excel → YAML library
.venv/bin/python tools/convert_library_v2.py tools/excel/cis/cis-benchmark-<tech>.xlsx \
    --output backend/library/libraries/cis-benchmark-<tech>.yaml
```

Only the **Appendix: Summary Table** is parsed (plus the cover page for name/version/date). Requirement nodes get:

- `ref_id` / `depth` from the recommendation numbering (depth = dot count + 1)
- `name` = recommendation title, `(Automated)`/`(Manual)` suffix stripped
- `assessable: x` iff the row carries an Automated/Manual tag; untagged rows are sections
- implementation group `A` (Automatic) or `M` (Manual) — the same `cat` group definition as cis-benchmark-kubernetes

Metadata (title, `vX.Y.Z`, publication date) is auto-read from the cover-page line `vX.Y.Z - MM-DD-YYYY`; `--ref-id`/`--name` override the auto-derived slug/title. Established slug convention: `cis-benchmark-aws-foundations`, `cis-benchmark-github`, `cis-benchmark-gcp-foundation`, `cis-benchmark-microsoft-365`, `cis-benchmark-windows-11`, `cis-benchmark-ubuntu-24.04`, …

## PDF quirks the extractor already handles (don't re-debug these)

- **Wrapped ref_ids**: deep numbers wrap inside the ref column (`18.10.10.1.1` + `0` → `18.10.10.1.10`, `18.10.42.6.1.` + `1` → `18.10.42.6.1.1`). Consecutive numeric fragments are buffered and accepted only when the concatenation is a valid depth-first successor of the previous ref.
- **Checkbox glyphs**: `o` on its own line, or glued to short titles (`... (Manual) o`), or private-use/ballot-box glyphs (Windows benchmarks). Stripped before tag matching.
- **ToC false positives**: the summary-table page is detected by an exact `Appendix: Summary Table` line *plus* the `CIS Benchmark Recommendation` header on the same page, so ToC entries don't match.
- **Empty sections**: sections with no assessable descendant (e.g. "Introduction", "CIS ... Benchmarks") are pruned by default (`--keep-empty-sections` to keep).
- **>200-char titles**: name is word-boundary-truncated with `…`, full title moved to `description` (DB limit enforced by convert_library_v2).
- Titles wrapped across lines are re-joined (hyphen-aware: `Organizations-` + `integrated` joins without a space).

The script exits 2 with `WARNING:` lines when it sees numeric lines it couldn't place (possible numbering gaps) — treat any warning as a parse review, not noise.

## Validation (always run the deep check)

```bash
.venv/bin/python .claude/skills/cis-benchmark-framework/scripts/deep_check.py \
    path/to/benchmark.pdf backend/library/libraries/cis-benchmark-<tech>.yaml
```

`deep_check.py` rebuilds ground truth from two sources *independent of the extractor* — the PDF's Table of Contents (refs + full titles + tags, including sections) and the recommendation body headings (anchored at `Profile Applicability:`) — and verifies against the YAML: ref coverage both ways, exact titles (whitespace/hyphen/quote-normalized), Automated/Manual tags, assessability, legitimacy of pruned sections, node ordering, and cover metadata. Expect `CLEAN`; `toc > yaml` by the pruned-section count is normal.

Interpreting findings:

- **TITLE-DIFF confirmed by both ToC and body** → the summary table itself is wrong (CIS errata); fix with `--rename` (below), body is authoritative.
- **YAML-ONLY + NO-BODY on the same ref** → summary-table-only phantom row (CIS editorial leftover). Keep it (the summary table is the extraction source of truth) but note it.
- Anything else → suspect the extractor; debug before shipping.

## Errata overrides

When the summary table contradicts the recommendation body, override at extraction time so the fix is reproducible:

```bash
--rename "4.1.2.1=(L2) Ensure Super Admin account recovery is disabled"
```

Known CIS PDF errata (re-apply on re-extraction):

- **Google Workspace v1.3.0 `4.1.2.1`**: summary table says "recovery is enabled"; ToC + body say "**disabled**" (the real control). Use the `--rename` above.
- **Ubuntu 24.04 v2.0.0 `1.5.10`** ("Ensure core file size is configured"): exists only in the summary table — ToC jumps 1.5.9 → 1.5.11 and there is no body section. Kept intentionally; deep_check reports it as the only expected non-CLEAN finding.

## Outputs & conventions

- Excel → `tools/excel/cis/<ref_id>.xlsx` (committed, alongside the kubernetes precedent)
- YAML → `backend/library/libraries/<ref_id>.yaml` (loadable library, PR-able)
- Library `version` starts at `1`; benchmark version lives in `description` (e.g. "CIS GitHub Benchmark v1.2.0"), never in the URN/ref_id
- `copyright: © CIS Security`, `provider: CIS`, `packager: intuitem`
