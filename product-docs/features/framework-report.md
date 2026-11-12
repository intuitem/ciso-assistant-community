---
description: Cross-audit aggregate for one framework — compliance %, average implementation score, in-scope audits, status breakdown
---

# Framework report

The **Framework report** is the answer to _"how is this framework doing across our organisation?"_ Pick any framework loaded into the platform, and the report rolls up every audit using it into a single view: compliance percentage, average implementation score, sections breakdown, and the full list of audits in scope. You can read it as a **Requirements tree** or pivot it **Per domain**, and — when domain-tree inheritance is enabled — fold parent-domain results into a single **Combined view**.

It's the framework-level layer of the platform's advanced analytics — sandwiched between the [per-audit Advanced Analytics](audit-analytics.md) dashboard and the [estate-wide Insights](insights.md) menu.

## Where this sits in the analytical stack

| Surface | Scope | Edition | Gating |
|---|---|---|---|
| **[Audit advanced analytics](audit-analytics.md)** | One audit | Community | `advanced_analytics` flag |
| **Framework report** (this page) | One framework, every audit using it | Community | None (permission-gated) |
| **[Insights](insights.md)** menu | Cross-cutting (impact graph, priority/effort, Gantt timeline) | Enterprise (PRO) | None (permission-gated) |

## Where to find it

- From the main menu: **Compliance > Summary** opens on the **By framework** tab, which lists every framework used by an audit you can read. Click one to open its report. The **By domain** tab shows each domain's audits.
- From a framework: open its detail page and click the **Insights** button at the top.

## What it shows

| Surface | What it answers |
|---|---|
| **Scoring scale + IGs subtitle** | The framework's score range (e.g. 0–100) and how many implementation groups it defines |
| **Compliance %** | Aggregate compliance percentage. Formula: _compliant + ½·partial, excluding N/A and not-assessed_ |
| **Average implementation score** | Mean implementation score over scored requirements only (so partially-scored audits don't drag the mean down with null values) |
| **In-scope audits** | The count of audits the report rolled up |
| **Detected audits drawer** | Per-audit list with status, folder path, and `counted vs excluded` marker — so you can see what the status filter left out |
| **Per-section breakdown** | Requirement rows grouped by their immediate parent section |
| **Implementation-group filter** | Narrow the report to a single IG via the **Implementation group** dropdown |
| **Verdicts** | For frameworks with outcome rules, how many of the filtered audits meet each verdict, and the average of each computed number. **By audit** shows each audit's verdicts and values; **By domain** counts them per domain at the chosen depth |
| **Excel export** | **Export (Excel)** downloads what the filters show: audits (with authors, labels, dates, scores and one column per verdict), requirements, domains with their requirements, verdicts per domain, and one row per requirement per audit |

## Filters

The **Filters** panel at the top of the report drives every figure below it: indicators, distribution, verdicts, tables and the Excel export.

- **Domains**: tick one or more domains, at any depth, or search them by name. An audit is kept when one of the ticked domains is on its path, so you can combine branches of the tree (for example two regional nodes under different parents). Domains under a ticked one show as already included.
- **Labels** and **Authors**: keep the audits carrying one of the ticked labels, or written by one of the ticked authors.
- **Implementation group**: narrow the report to a single group.
- **Status**: **All but deprecated** (the default) or only live audits, in progress, in review or done.
- **Deadline**: pick **ETA** or **Due date**, then **Overdue** (done audits are never overdue), **Next 3 / 6 / 12 months**, or **Custom** for a window in months from today. In a custom window, `3 → 6` keeps audits due between three and six months from now, and a negative bound reaches back into overdue audits. Audits without that date are left out while the filter is on.

Active filters show as chips under the panel; click a chip's cross to remove it, or **Reset filters** to clear them all. The detected audits drawer greys out the audits the filters leave out.

## Two ways to read it

The **View** toggle in the filter bar switches the body of the report between two lenses on the same numbers:

- **Requirements tree** — the default. Sections roll up their requirements; click a section to expand it, then click a requirement row to drill into its **Per-assessment breakdown** (one row per audit, with domain, result, score, controls and evidence counts, and a link straight to that requirement assessment). Several requirements can be open at once. **Expand all** / **Collapse all** act on every section at once; **Collapse all** also closes open requirements.
- **Per domain** — pivots the same rows by the domain (Folder) they live in. **Group by domain depth** controls how far down the tree the grouping cuts (`root` … `leaf domain`), and **Sort by** orders the rows by domain name (alphabetical), compliance %, or average score, ascending or descending. Click a domain to filter the report on it and switch to the **Requirements tree**, which then shows that domain's sections and requirements with their compliance and average scores.

## Exporting evidences

Tick what to export in the **Requirements tree**: a requirement covers all its audits, a section ticks all its requirements, and in a requirement's **Per-assessment breakdown** each audit can be ticked on its own (the requirement then shows as partly ticked). The box in the **Ref.** header ticks every requirement shown. **Export evidences (N requirements)** above the table downloads one zip for the selection, over the filtered audits, with one folder per domain and audit. Each file is stored once per audit, however many of its requirements it supports; the index lists one row per requirement. When the selection has no evidence, a message says so and nothing is downloaded. It includes evidences attached to the requirements and those attached to their applied controls, limited to the evidences you can read. An `index.xlsx` at the root of the zip lists every evidence with its domain, audit and requirement, the applied control it comes from when it is not attached to the requirement directly, and a clickable link to its file in the zip, or to its URL when it has no file.

## What gets counted

By default every audit you can read rolls into the numbers, except deprecated ones: when you cut a new audit cycle on the same domain, mark the previous one deprecated so it doesn't double-count its requirements alongside the new one. Set **Status** to the live statuses to keep only audits that are:

- `in_progress`
- `in_review`
- `done`

Planned audits are then left out as well. In the default mode, planned audits count in the figures but not in the verdicts, since they have not started. Excluded audits stay visible in the drawer. In a campaign report, planned audits count as live.

## Combined view: domain-tree inheritance

When the same framework is audited at several levels of a domain hierarchy — say an org-wide audit on the root domain, a business-unit audit below it, and a system audit below that — a lower audit can **inherit** results and scores for requirements an ancestor audit already covers. This is useful when common controls are assessed once high up and you don't want every child audit to re-prove them.

This only appears when your administrator has enabled **Domain-tree audit inheritance** and chosen a strategy other than _No inheritance_ — see [the inheritance setting](../configuration/settings/general.md#domain-tree-audit-inheritance). When it's active and at least one requirement on this framework actually inherits something, a **Combined view** control shows up in the filter bar with an **Apply domain inheritance** checkbox (on by default).

Inheritance is **non-destructive**. Each audit's own stored results are never changed; the report computes an _effective_ result and score on top of them and remembers where each came from. Toggling **Apply domain inheritance** off returns every figure — KPIs, distributions, and the detail cells — to each audit's own values.

### How a source is chosen

For a requirement, the platform looks up the domain tree from the audit (nearest ancestor first, including the root domain). In each ancestor domain it considers only **live** audits on the same framework (`in_progress` / `in_review` / `done`) and picks the **most recently updated** one. The configured strategy then decides which value along that chain wins:

| Strategy | Effective result |
|---|---|
| **No inheritance** | Inheritance off — each audit stands alone |
| **Parent always wins** | The nearest ancestor that has a verdict overrides the child |
| **Child always wins** | The child's own verdict stands; ancestors only fill gaps it left unassessed |
| **Best case (optimistic)** | The strongest verdict anywhere in the chain (`compliant` > `partially compliant` > `non-compliant`) |
| **Worst case (prudent)** | The weakest verdict anywhere in the chain |

A requirement marked `not assessed` carries no opinion, so it never wins a comparison — it's the gap that ancestors fill. The score follows the same audit that won the result (a score is only meaningful paired with the verdict it was given for), and when audits use different scoring scales every score is normalised onto the **top-most ancestor's scale** before it's shown.

{% hint style="info" %}
The same `not assessed` and live-status rules power both this report and the per-audit [Advanced Analytics](audit-analytics.md) inheritance panel, so the two always agree.
{% endhint %}

### Reading an inherited row

Drill into a requirement (Requirements tree → expand a section → click the row) and the **Per-assessment breakdown** marks each inherited row:

- A **branch icon** next to the result links to the source audit it was inherited from; hovering it shows the full inheritance path (`domain · audit: result`, nearest first).
- An **info icon** next to the score appears when the audit's own result differs from the effective one — hover it to see the original _own result_ and score before inheritance was applied.

## Permissions and visibility

The report respects the same IAM rules as the rest of the platform:

- You only see audits in domains you can read.
- For each audit, your viewer role (auditor by default, **respondent** when you're an auditee on that folder) is resolved per-CA.
- If the audit's [field visibility](../guides/customize-audit.md) hides a column for your role, that column comes back as `null` on the report row — but the row still counts toward domain and section totals. The report tells you _how many requirements_ are in each state without revealing values you're not permitted to see.

## When you'd use it

- **Programme-level review** — board-facing or steering-committee read on "how well are we doing against ISO 27001 / SOC 2 / NIS2 across the whole organisation?"
- **Comparing implementation groups** — switch IG filter to see how IG1 / IG2 / IG3 fare separately.
- **Pre-cycle planning** — spot which audits to refresh by looking at the per-section breakdown.

## Related

- [Audit advanced analytics](audit-analytics.md) — same analytical lens, scoped to a single audit
- [Insights](insights.md) — Enterprise cross-cutting analytical views (impact graph, priority/effort, Gantt timeline)
- [Frameworks](../concepts/frameworks.md)
- [Audits](../concepts/audits.md)
- [Customize your audit](../guides/customize-audit.md) — field visibility, which feeds the redaction logic on this report
