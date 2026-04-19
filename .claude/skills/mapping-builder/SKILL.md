---
name: mapping-builder
description: Build a reviewed crosswalk (RequirementMappingSet YAML library + review xlsx/csv) between two CISO Assistant framework YAML files using Claude itself as the reasoning engine. Zero infrastructure — stdlib + pyyaml only, no embedders, no LM Studio, no Qdrant. Use when the user asks to map / crosswalk / generate a mapping between two frameworks (e.g. ccb-cff-2023-03-01.yaml ↔ cyfun2025.yaml), wants to contribute a community mapping to backend/library/libraries/, or says things like "build a mapping between framework X and Y", "create a crosswalk YAML", "generate requirement_mapping_set". Output matches the schema in backend/library/libraries/mapping-*.yaml exactly so the result is PR-able.
---

# Mapping Builder

## What this skill does

Generate a CISO Assistant `requirement_mapping_set` library YAML — plus a human-review xlsx/csv — by reasoning over two framework YAMLs entirely in this conversation. No embedders, no local LLMs, no vector DBs.

The output YAML drops directly into `backend/library/libraries/` and is loadable by the platform's library loader.

**When NOT to use this skill:**
- For mapping huge frameworks (>500 assessable items per side). The conversation context fills up. Use `tools/mapping_builder/map_v2.py` instead — it has hybrid retrieval and runs locally.
- For batch/automated runs that need to be deterministic across sessions. Use the local CLI.

## How to use the helpers

Three stdlib + pyyaml scripts under `scripts/`:

```bash
# Parse a framework YAML → JSON with assessable items grouped by section
python scripts/parse_framework.py path/to/framework.yaml > parsed.json

# Emit the mapping library YAML from a verdicts spec
python scripts/write_mapping_yaml.py spec.json output.yaml

# Emit a review xlsx (or csv if openpyxl missing)
python scripts/write_review.py spec.json source_parsed.json target_parsed.json review.xlsx
```

Always invoke them with the project's venv: `.venv/bin/python scripts/...`.

The `spec.json` for `write_mapping_yaml.py` and `write_review.py` is built up across the workflow below — see the docstrings of the scripts for the exact field shape.

## Workflow

Run the steps in order. Do NOT skip the section-affinity step — it is the single most important quality lever and prevents wasting context on irrelevant pairs.

### Step 1 — confirm the request and check for duplicates

Before doing any work, confirm with the user:
- Source framework YAML path
- Target framework YAML path
- Direction matters: source maps INTO target

Then `Glob` for `backend/library/libraries/mapping-*.yaml` and check if a published mapping for this exact pair already exists. If yes, surface it to the user — they may want to extend rather than recreate.

### Step 2 — parse both frameworks

```bash
.venv/bin/python .claude/skills/mapping-builder/scripts/parse_framework.py \
  backend/library/libraries/SOURCE.yaml > /tmp/src.json
.venv/bin/python .claude/skills/mapping-builder/scripts/parse_framework.py \
  backend/library/libraries/TARGET.yaml > /tmp/tgt.json
```

`Read` both JSONs (or summarize via the CLI if too large) and confirm the framework sizes with the user. Note `n_assessable` and `n_sections` for each side.

**Hard limit check**: if either side has > 500 assessable items, stop and recommend the local CLI (`tools/mapping_builder/map_v2.py`). Don't try to power through — context will fail mid-mapping.

### Step 3 — section-affinity narrowing (DO NOT SKIP)

Read the `sections` array from each parsed JSON (typically 5-30 entries per side, so cheap to consider in full).

Build a section affinity table by reasoning over section names alone — for each source section, identify the 1-3 target sections most likely to contain real mappings:

```
SOURCE section ID.AM (Asset Management)
  → likely targets: ID.AM (direct), GV.OC (governance overlap)
SOURCE section PR.AC (Access Control)
  → likely targets: PR.AA (Access Authentication)
... etc
```

Print this affinity table to the user, ask them to sanity-check it. If they correct anything, update before proceeding. **This is where most recall is won or lost** — embedders systematically over-match on shared jargon; reading section names is more discriminating.

### Step 4 — per-section deep dive

For each `(source_section, [target_sections])` entry from Step 3, do the following in order:

1. Pull the source items that belong to `source_section` and the target items that belong to any of the `target_sections`. With section narrowing, this is typically 5-20 sources × 5-30 targets = 25-600 candidate pairs per section.
2. Read each source item's `full_sentence`, then read all candidate targets' `full_sentence`.
3. For each source, decide which targets are real mappings. Output a JSON list of verdicts:

```json
{
  "source_requirement_urn": "...",
  "target_requirement_urn": "...",
  "relationship": "equal | intersect | subset | superset",
  "strength_of_relationship": 0-10,
  "rationale": "one-sentence why"
}
```

Relationship rubric (matches the platform enum):
- **equal**: same obligation, interchangeable for audit. Reverse maps to equal.
- **intersect**: meaningful overlap, neither covers the other. Reverse maps to intersect.
- **subset**: source is contained within target's scope. Reverse maps to superset.
- **superset**: source is broader than target. Reverse maps to subset.
- (`not_related` is never emitted — just omit the pair from the verdicts.)

`strength_of_relationship` is a 0-10 confidence in the *existence* of the mapping (NOT in the equal/intersect label).

Append verdicts to a running `verdicts` list. Persist the running list to `/tmp/<mapping_name>_verdicts.jsonl` after each section so progress is recoverable.

### Step 5 — borderline review with the user

Before emitting the YAML, surface ambiguous calls to the user. Specifically:
- All verdicts with `strength_of_relationship` ≤ 6
- Pairs where the equal vs intersect call could go either way
- Source items that ended up with zero verdicts (might indicate a missed section pairing)

Show source/target text side-by-side and your rationale. Let the user override `relationship`, override `strength_of_relationship`, or drop the pair entirely. Apply edits to the running verdicts list.

### Step 6 — emit YAML + review file

Build the `spec.json`:

```python
{
  "ref_id": f"mapping-{source_ref_id_lower}-and-{target_ref_id_lower}",
  "name": f"{source_framework_name} <-> {target_framework_name}",
  "description": "...",
  "version": 1,
  "publication_date": today_iso,
  "copyright": "...",          # ask the user
  "provider": "...",            # ask the user
  "packager": "...",            # ask the user
  "source_library_urn":   <from src.json[\"library_urn\"]>,
  "source_framework_urn": <from src.json[\"framework_urn\"]>,
  "target_library_urn":   <from tgt.json[\"library_urn\"]>,
  "target_framework_urn": <from tgt.json[\"framework_urn\"]>,
  "verdicts": [...]
}
```

Pull the URNs straight from the parsed JSON — do NOT construct them by hand. The library URN slug is not always the same as the framework `ref_id` (e.g. `cyfun2025` → `urn:intuitem:risk:library:ccb-cyfun2025`).

Then run:

```bash
.venv/bin/python .claude/skills/mapping-builder/scripts/write_mapping_yaml.py \
  /tmp/spec.json \
  backend/library/libraries/mapping-<source>-and-<target>.yaml

.venv/bin/python .claude/skills/mapping-builder/scripts/write_review.py \
  /tmp/spec.json /tmp/src.json /tmp/tgt.json \
  /tmp/mapping-<source>-and-<target>_review.xlsx
```

The mapping YAML automatically contains both the forward AND reverse mapping sets (subset/superset are auto-flipped on the reverse).

### Step 7 — final summary, no auto-PR

Report to the user:
- Total mappings produced (forward; the reverse is auto-derived)
- Distribution by relationship type
- Path to the YAML library file
- Path to the review xlsx
- Suggested commit message

Do NOT auto-commit or auto-push. The user is putting their name on a community contribution; they confirm before pushing. If they ask, then `git checkout -b <branch>` and stage the new YAML.

## Output schema reference

The emitted YAML must match this top-level shape exactly (the `write_mapping_yaml.py` script enforces it):

```yaml
urn: urn:intuitem:risk:library:<ref_id>
locale: en
ref_id: <ref_id>
name: <name>
description: <description>
copyright: ...
version: 1
publication_date: YYYY-MM-DD
provider: ...
packager: ...
dependencies:
  - <source library URN>
  - <target library URN>
objects:
  requirement_mapping_sets:
    - urn: urn:intuitem:risk:req_mapping_set:<ref_id>
      ref_id: <ref_id>
      name: <name>
      description: ...
      source_framework_urn: <source framework URN>
      target_framework_urn: <target framework URN>
      requirement_mappings:
        - source_requirement_urn: ...
          target_requirement_urn: ...
          relationship: equal | intersect | subset | superset
          strength_of_relationship: 0-10        # optional
          rationale: ...                          # optional, useful for review
    - # reverse mapping set, auto-derived
      ...
```

Look at any existing `backend/library/libraries/mapping-*.yaml` for a real example.

## Common mistakes to avoid

- **Skipping section affinity** and trying to consider source × target pairs blindly — context fills up and recall drops.
- **Constructing URNs by string concatenation** instead of pulling them from the parsed framework JSONs. Library and framework URN slugs are not always equal to ref_id.
- **Only emitting the forward mapping set.** The platform expects two sets in the library (forward + reverse). The `write_mapping_yaml.py` script generates the reverse automatically — don't bypass it.
- **Forgetting `subset` ↔ `superset` flip on reverse.** The script handles this; if you write the YAML by hand, you'll get it wrong.
- **Auto-committing the result.** This is a community contribution; the user always confirms.
- **Using `not_related` as a relationship value.** It's not in the published schema. Just omit pairs that aren't real mappings.

## Quick reference

| File | Purpose |
|---|---|
| `scripts/parse_framework.py` | Framework YAML → JSON with items grouped by section |
| `scripts/write_mapping_yaml.py` | Verdicts spec → published-format library YAML (forward + reverse) |
| `scripts/write_review.py` | Verdicts spec + parsed frameworks → xlsx (or csv fallback) for human audit |
