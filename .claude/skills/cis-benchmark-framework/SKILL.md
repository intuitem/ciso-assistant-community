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

## Validation (do all three)

1. **Script counters**: the run prints `N nodes: X sections, Y automated, Z manual` — sanity-check against the benchmark's expected scale.
2. **Structural YAML check**: unique URNs, every depth>1 node's `parent_urn` resolves, every assessable node has an `A`/`M` group, names ≤200 chars.
3. **Completeness cross-check**: count `Profile Applicability:` occurrences in the PDF body — it should equal the assessable count. Known benign diffs when diffing ref-by-ref with a heading-walk-back checker:
   - wrapped body headings make the checker misread refs (`1.11 Ensure ... Within a Period of | 90 Days` → checker reports ref `90`); verify the real ref was extracted before suspecting the extractor;
   - CIS PDFs occasionally list a recommendation in the summary table that has no body section (e.g. Ubuntu 24.04 v2.0.0 `1.5.10`) — keep it, the summary table is the source of truth.

## Outputs & conventions

- Excel → `tools/excel/cis/<ref_id>.xlsx` (committed, alongside the kubernetes precedent)
- YAML → `backend/library/libraries/<ref_id>.yaml` (loadable library, PR-able)
- Library `version` starts at `1`; benchmark version lives in `description` (e.g. "CIS GitHub Benchmark v1.2.0"), never in the URN/ref_id
- `copyright: © CIS Security`, `provider: CIS`, `packager: intuitem`
