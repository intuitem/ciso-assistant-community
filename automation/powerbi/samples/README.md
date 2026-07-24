# Starter template (starter.pbit)

The opinionated starting point shipped with the connector: a lean model, four
report pages answering the most common GRC questions, and the fiddly Power BI
settings pre-configured so end users never meet them.

Authored and validated live against a real instance (2026-07-23). This file
documents the template's actual content so a maintainer can rebuild or evolve
it. Keep it in sync with `starter.pbit` — it is the template's source of truth
in review.

## Model

**Tables loaded (12):**

- Facts: Requirement Assessments, Applied Controls, Incidents,
  Vulnerabilities, Risk Scenarios, Assets
- Dimensions: Compliance Assessments, Frameworks, Folders, Threats
- Bridges: Risk Scenario - Threat, Risk Scenario - Vulnerability

Deliberately not loaded (users add them from the navigator when needed):
Evidences, Security Exceptions, Requirement Nodes, Risk Assessments,
Perimeters, Reference Controls, Findings, Findings Assessments, Labels, and
the remaining bridges. Lean loads faster and confuses less; the connector
exposes everything either way.

**Settings baked into the file:**

- *Autodetect new relationships after data is loaded* is **off** (Options →
  Current file → Data Load). Every table shares column names (`ref_id`,
  `name`, `folder_id`…), so autodetect invents bogus joins like
  `Vulnerabilities[ref_id] → Assets[ref_id]`. The only valid joins in this
  model are `id` ↔ `*_id`.
- Report-level filter: `Requirement Assessments[assessable] = True` — audits
  also carry rows for non-assessable structural headings; this cleans every
  compliance visual in one place without touching other facts.
- Data labels use *Display units: None* on count visuals (Auto rounds GRC-scale
  numbers to "2K/0K").

**Relationships** (all `id` ↔ `*_id`, many-to-one, Single cross-filter — v1
ships exactly these six):

- `Applied Controls[folder_id]` → `Folders[id]`
- `Compliance Assessments[folder_id]` → `Folders[id]`
- `Compliance Assessments[framework_id]` → `Frameworks[id]`
- `Requirement Assessments[compliance_assessment_id]` → `Compliance Assessments[id]`
- `Risk Scenario - Threat[risk_scenario_id]` → `Risk Scenarios[id]`
- `Risk Scenario - Threat[threat_id]` → `Threats[id]`

Known v1 gaps, accepted deliberately (visuals use the facts' inline
`folder_name` columns instead): the other facts are not wired to `Folders`,
so a single Folders slicer does not drive every page; the
`Risk Scenario - Vulnerability` bridge is loaded but unwired. Wire
`folder_id → Folders[id]` on the remaining facts and both bridge edges when
promoting the template. Set **Both** cross-filter only on a bridge→fact edge
if a dimension slicer must filter facts through it.

**Calculated pieces:**

- `Vulnerabilities[severity_rank]` — Power Query conditional column
  (Critical→0, High→1, Medium→2, Low→3, else 4), used as *Sort by column* for
  `severity`. Reusable pattern for any ordered label (priority, effort).
- Measure `Vulns This Severity or Worse` (cumulative funnel):

  ```dax
  VAR CurrentRank = SELECTEDVALUE(Vulnerabilities[severity_rank])
  RETURN CALCULATE(
      COUNTROWS(Vulnerabilities),
      REMOVEFILTERS(Vulnerabilities[severity], Vulnerabilities[severity_rank]),
      Vulnerabilities[severity_rank] <= CurrentRank
  )
  ```

- Quick measure: running total of Count of `Incidents[id]` over `reported_at`.

## Pages

1. **compliance overview** — 100% stacked bar: Y = `folder_name` →
   `compliance_assessment_name` (drill), value = count of Requirement
   Assessments, legend = `result`; plus a detail table (folder, audit,
   `requirement_ref_id`, `requirement_name`, `result`, `updated_at`)
   cross-filtered by clicking bars.
2. **controls breakdown** — 100% stacked bar on the Folders hierarchy
   (`parent_folder_name` → `name`), value = count of Applied Controls,
   legend = `status`; plus a decomposition tree (Analyze = count of controls,
   Explain by = `folder_name`, `category`, `status` — viewer picks the split
   order at explore time).
3. **risk: threats breakdown** — treemap: Group = `Risk Scenarios[folder_name]`
   → `Threats[name]`, value = count of `Risk Scenario - Threat` rows (bridge
   count = distinct scenarios per threat).
4. **incidents and vulns** — line chart of cumulative incidents by month of
   `reported_at`; funnel of `severity` (sorted by `severity_rank`) with the
   cumulative measure — each stage reads "this severe or worse", widest
   "everything" stage on top.

## Rebuilding / evolving

1. Install the current connector (see `../CONTRIBUTING.md`).
2. New blank report → turn OFF relationship autodetect (above) **before**
   loading → Get Data → CISO Assistant → load the 12 tables.
3. Wire the relationships, add the calculated column + measures, build the
   pages, apply the report-level `assessable` filter.
4. **File → Export → Power BI template** → `starter.pbit` here. Never commit
   a `.pbix` — it embeds the authoring instance's data (enforced via
   `.gitignore`); the `.pbit` strips data and prompts for URL + PAT on
   first open.
5. **Audit the export** — a `.pbit` is a zip whose `DataModelSchema` and
   `Report/Layout` are UTF-16 JSON. Check tables/relationships/measures
   against this README before committing; autodetect-phantom relationships
   (same-named columns like `ref_id`) have slipped into exports before:

   ```bash
   unzip -o starter.pbit -d /tmp/pbit
   python3 -c "
   import json
   m = json.loads(open('/tmp/pbit/DataModelSchema','rb').read().decode('utf-16-le'))['model']
   [print(r['fromTable'],r['fromColumn'],'->',r['toTable'],r['toColumn'])
    for r in m['relationships'] if 'LocalDateTable' not in r['toTable']]"
   ```

Ideas validated but intentionally left out of v1 (add when asked for):
framework-level drill page (`framework_name` → folder → audit; caveat:
aggregates across audit versions), a shared calendar/date table for
cross-fact time intelligence, per-fact Label bridges for taxonomy slicing.
