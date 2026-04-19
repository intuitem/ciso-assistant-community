---
name: reference-controls-enricher
description: Enrich a CISO Assistant framework YAML by linking each assessable requirement to reference control URNs from the central doc-pol library (CISO Assistant Key Reference Controls). Produces a reviewable xlsx and patches the framework YAML in place. Use when the user asks to "add reference controls to framework X", "link doc-pol controls to requirements", "wire up applied-control suggestions for framework Y", or wants to contribute a reference-control-enriched framework to backend/library/libraries/.
---

# Reference Controls Enricher

## What this skill does

For a given framework YAML, walk every assessable requirement and propose 1–5 reference control URNs from the central doc-pol library (the CISO Assistant Key Reference Controls). Outputs:

- a reviewable xlsx per framework
- a YAML patch applied in place (adds URNs to each requirement's `reference_controls` field, adds `doc-pol` to `dependencies`)
- a coverage report

Claude is the reasoner — no embedders, no local models. The pipeline is pure stdlib + pyyaml (+ optional openpyxl for xlsx).

**When NOT to use this skill:**

- For frameworks with >500 assessable items: the conversation context fills up. Chunk the run across sessions or adapt `tools/mapping_builder/map_v2.py` for offline use.
- For frameworks that already reference `doc-pol:*` URNs on most requirements: run `coverage_report.py` first; if coverage is already good, don't rewrite.

## How to use the helpers

Stdlib + pyyaml scripts under `.claude/skills/reference-controls-enricher/scripts/`.

```bash
SKILL=.claude/skills/reference-controls-enricher/scripts
MB=.claude/skills/mapping-builder/scripts  # reused for framework parsing

# Parse a framework YAML (same parser as mapping-builder)
.venv/bin/python $MB/parse_framework.py backend/library/libraries/<framework>.yaml > /tmp/fw.json

# Parse the key-controls library
.venv/bin/python $SKILL/parse_controls.py backend/library/libraries/doc-pol.yaml > /tmp/controls.json

# Write a reviewable xlsx from the running verdicts
.venv/bin/python $SKILL/write_review.py /tmp/fw.json /tmp/controls.json /tmp/verdicts.jsonl /tmp/<name>_review.xlsx

# Apply URN assignments to the framework YAML (adds doc-pol dependency if needed)
.venv/bin/python $SKILL/apply_enrichment.py backend/library/libraries/<framework>.yaml /tmp/verdicts.jsonl --bump

# Audit coverage + low-confidence verdicts + zero-URN requirements
.venv/bin/python $SKILL/coverage_report.py /tmp/fw.json /tmp/verdicts.jsonl
```

## Verdicts file format

One JSON object per line. `target_urns` is the list of doc-pol URNs to link. Empty list → requirement is consciously left unlinked.

```json
{"source_urn": "urn:intuitem:risk:req_node:<fw>:<ref>",
 "target_urns": ["urn:intuitem:risk:function:doc-pol:pol.access",
                 "urn:intuitem:risk:function:doc-pol:tech.mfa"],
 "confidence": 8,
 "rationale": "Access control obligation with explicit MFA — maps to access policy + MFA capability."}
```

Persist `/tmp/<framework>_verdicts.jsonl` and append after each section so progress is recoverable if the conversation gets interrupted.

**Always read `source_urn` from the parsed framework JSON's `items[].urn`** — do NOT construct it from `ref_id`. Ref_ids may use mixed case (e.g. `2.A.1`) but the URN suffix is always lowercase (e.g. `2.a.1`). Constructing URNs by string concatenation is a known bug trap.

## Parsed framework shape (important)

`parse_framework.py` emits a **flat** `items` list, each item carrying `section_urn`, `section_ref_id`, `section_name` — items are **not** nested inside `sections[].items`. Iterate `parsed["items"]`, not `parsed["sections"][i]["items"]`. This differs from common heuristic expectations and has bitten at least one implementation mid-session.

## Workflow

### Step 1 — confirm the request

Confirm with the user:

- Target framework YAML path (the one being enriched)
- Whether the framework already has a `doc-pol` dependency — if yes, existing `reference_controls` on requirements must be **preserved** (this skill appends, never replaces)
- Whether they want the skill to **apply in place** or emit a review-only pass

Grep the framework for `urn:intuitem:risk:function:doc-pol:` to check prior linkage. Report coverage before touching anything.

### Step 2 — parse both sides

```bash
.venv/bin/python .claude/skills/mapping-builder/scripts/parse_framework.py \
  backend/library/libraries/<framework>.yaml > /tmp/fw.json

.venv/bin/python .claude/skills/reference-controls-enricher/scripts/parse_controls.py \
  backend/library/libraries/doc-pol.yaml > /tmp/controls.json
```

Read both JSONs. Note `n_assessable` for the framework and the doc-pol prefix breakdown (doc / pol / proc / tech / phys / train).

**Size gate**: if `n_assessable > 500`, stop and recommend a chunked or offline approach.

### Step 3 — build a section → prefix-family affinity map (DO NOT SKIP)

Read the `sections` array from the parsed framework (typically 5–30 entries). For each section, reason about which doc-pol prefixes are most likely relevant. doc-pol prefixes group by control-type:

| Prefix | Typical content |
|---|---|
| `pol.*` | Policies (access, crypto, supplier, malware, vuln, etc.) |
| `proc.*` | Operational procedures (incident, change, pam, backup, etc.) |
| `doc.*` | Registers, records and structured documents (RACI, ROPA, asset register) |
| `tech.*` | Technical capabilities (MFA, SIEM, WAF, DLP, IAM, EDR, etc.) |
| `phys.*` | Physical and environmental controls |
| `train.*` | Training programs |

For a governance section, expect mostly `pol.*` + `doc.*`. For a monitoring section, `pol.monitor` + `proc.logging` + `tech.siem` + `train.logging`. Etc.

Print the affinity table to the user; they sanity-check before Step 4. This narrows the 170+ controls per section to ~10–25 candidates.

### Step 4 — per-section deep dive

For each section, pull:

1. The section's assessable items (read their `full_sentence`).
2. Candidate doc-pol controls filtered by the section's prefix families — read `name + description + annotation` for each.

For each requirement, decide which controls apply (1–5 is typical; keep it tight). Emit a verdict per requirement:

```json
{"source_urn": "...",
 "target_urns": ["...", "..."],
 "confidence": 0-10,
 "rationale": "one-sentence why"}
```

**Confidence scale (calibrated from real runs):**

- **10**: obvious / near-identical semantic match (e.g. "implement the PSSI" → `pol.main`). Use sparingly — reserved for the ~15% of cases with zero interpretation.
- **8–9**: clean semantic match — this is the norm and should be where most verdicts land.
- **7**: plausible, some interpretation or scope trimming required.
- **6**: mitigation / exception patterns — recognise the pattern "when X is not possible, entity implements risk-reduction measures". These legitimately map to `proc.exception_mgmt` + the parent topic at confidence 6. Don't chase these to higher confidence — they're correctly low.
- **0–5**: weak — rare; only include if the requirement is thin and this is the best available.

**Single-URN verdicts are fine** when many requirements are sub-clauses of the same parent topic (e.g. ten `pol.access` sub-clauses in an IAM objective). Don't force artificial expansion to meet an imagined 2-URN minimum.

**Four-plus-URN verdicts must be justified explicitly** — e.g. a requirement listing "at minimum: crypto policy, access policy, audit policy, account policy" genuinely deserves 4 URNs. Default 4+ linkages are usually over-linking; 2–3 is the sweet spot.

Prefer strong high-level policy URNs (e.g. `pol.access`) over too-specific technicals when the requirement is broadly worded. Prefer specific tech URNs (e.g. `tech.mfa`) when the requirement explicitly mentions a capability. Don't over-link — 3 crisp URNs beat 8 soft ones.

**Affinity is a starting heuristic, not a fence** — if a requirement obviously needs a control from a different prefix family, pull it.

Append verdicts to `/tmp/<name>_verdicts.jsonl` section-by-section so progress is recoverable.

### Step 5 — borderline review with the user

```bash
.venv/bin/python .claude/skills/reference-controls-enricher/scripts/coverage_report.py \
  /tmp/fw.json /tmp/<name>_verdicts.jsonl --threshold 5
```

Surface to the user:

- Verdicts with `confidence < 5` — borderline calls to confirm or drop
- Requirements with **zero** target URNs — either a true gap (add to doc-pol backlog) or a miss (reconsider)
- Requirements with >5 URNs — likely over-linking

Apply the user's edits to the running jsonl before moving to Step 6.

**Slug usage as a sanity signal.** Check the most-cited doc-pol slugs — they should match the framework's character. Example: for a French NIS2-style framework (RECYF), `pol.access`, `pol.network`, `proc.pam` dominating is expected. For a privacy framework, expect `pol.privacy`, `proc.dpia`, `doc.ropa` at the top. If the top slugs don't match the framework's theme, something's off (too shallow, or affinity was wrong).

Also check the **unused slugs**: they should fall in out-of-scope domains relative to the framework. A security framework using 0 of the privacy/AI/OT slugs is normal. If a supposedly broad framework leaves 70%+ of slugs unused, reconsider affinity.

### Step 6 — write review xlsx

```bash
.venv/bin/python .claude/skills/reference-controls-enricher/scripts/write_review.py \
  /tmp/fw.json /tmp/controls.json /tmp/<name>_verdicts.jsonl \
  /tmp/<name>_review.xlsx
```

Open the xlsx with the user and walk through flagged rows (LOW / ZERO). Edit the jsonl if anything changes; re-run `write_review.py` to refresh.

### Step 7 — apply in place

Once the user is comfortable:

```bash
.venv/bin/python .claude/skills/reference-controls-enricher/scripts/apply_enrichment.py \
  backend/library/libraries/<framework>.yaml \
  /tmp/<name>_verdicts.jsonl \
  --bump
```

This:

- Appends `target_urns` to each matching requirement's `reference_controls` (dedup against existing)
- Adds `urn:intuitem:risk:library:doc-pol` to the framework's `dependencies` (if new URNs were added)
- Bumps the framework's `version` (if new URNs were added)

Run the standard post-check:

```bash
.venv/bin/python backend/manage.py storelibraries \
  --path backend/library/libraries/<framework>.yaml
```

Expect "Successfully stored library". If the library fails to load, inspect the stderr and revert via `git checkout -- backend/library/libraries/<framework>.yaml`.

### Step 8 — final summary, no auto-PR

Report:

- Enrichment coverage % (from `coverage_report.py`)
- Number of URNs added, number of requirements touched
- Path to the review xlsx
- Path to the verdicts jsonl (for replay / audit)
- Suggested commit message

**Do NOT auto-commit or auto-push.** The user confirms.

## Common mistakes to avoid

- **Over-linking.** 3 tight URNs beat 8 loose ones. The suggestions UI exposes all linked controls to the auditor — noise hurts.
- **Constructing source URNs from `ref_id`.** Case mismatches (`2.A.1` vs `2.a.1`) break resolution silently. Always use the `urn` field from the parsed framework JSON.
- **Iterating `sections[].items`.** `parse_framework.py` emits a flat `items` list. Iterate `parsed["items"]` and group by `section_ref_id` if you need section structure.
- **Missing the affinity step.** Without pre-filtering by prefix family, you'll waste context reading irrelevant controls for each requirement.
- **Replacing existing `reference_controls`.** `apply_enrichment.py` only appends, but if a future script or hand-edit clobbers the list, audit evidence gets orphaned.
- **Forgetting the dependency line.** `apply_enrichment.py` adds it automatically when any URN is added, but if you hand-edit the verdicts file, the library will still fail to load on import with URN-resolution errors.
- **Ignoring zero-URN requirements.** A truly uncovered requirement tells you either: (1) the framework is asking for something doc-pol doesn't have (flag for doc-pol extension), (2) the requirement is too abstract to link (leave empty by design), or (3) you missed a match (revisit).
- **Re-applying after editing verdicts.** `apply_enrichment.py` only appends and dedups — it cannot remove URNs from a prior apply. To change verdicts after an apply, `git checkout -- <framework.yaml>` first, then re-run with the updated jsonl.
- **Chasing confidence 10 for mitigation cases.** Requirements phrased "when X is not possible, implement mitigating measures" correctly map to `proc.exception_mgmt` + the parent topic at confidence 6. Don't force them higher — the lower score accurately signals the exception nature.

## Quick reference

| File | Purpose |
|---|---|
| `.claude/skills/mapping-builder/scripts/parse_framework.py` | Framework YAML → JSON with items grouped by section (reused) |
| `scripts/parse_controls.py` | doc-pol.yaml → JSON with controls indexed by URN + prefix |
| `scripts/write_review.py` | Verdicts + parsed framework + parsed controls → reviewable xlsx |
| `scripts/apply_enrichment.py` | Verdicts → patches framework YAML in place |
| `scripts/coverage_report.py` | Verdicts + parsed framework → coverage %, histogram, flagged items |
