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
| **Framework report** (this page) | One framework, every live audit using it | Community | None (permission-gated) |
| **[Insights](insights.md)** menu | Cross-cutting (impact graph, priority/effort, Gantt timeline) | Enterprise (PRO) | None (permission-gated) |

## Where to find it

1. Open the **Frameworks** list (`/frameworks`).
2. Click into a framework's detail page.
3. Click the **Insights** button at the top.

## What it shows

| Surface | What it answers |
|---|---|
| **Scoring scale + IGs subtitle** | The framework's score range (e.g. 0–100) and how many implementation groups it defines |
| **Compliance %** | Aggregate compliance percentage. Formula: _compliant + ½·partial, excluding N/A and not-assessed_ |
| **Average implementation score** | Mean implementation score over scored requirements only (so partially-scored audits don't drag the mean down with null values) |
| **In-scope audits** | The count of audits the report rolled up |
| **Detected audits drawer** | Per-audit list with status, folder path, and `counted vs excluded` marker — so you can see what the live-status filter left out |
| **Per-section breakdown** | Requirement rows grouped by their immediate parent section |
| **Implementation-group filter** | Narrow the report to a single IG via the **Implementation group** dropdown |

## Two ways to read it

The **View** toggle in the filter bar switches the body of the report between two lenses on the same numbers:

- **Requirements tree** — the default. Sections roll up their requirements; click a section to expand it, then click a requirement row to drill into its **Per-assessment breakdown** (one row per audit, with domain, result, score, controls and evidence counts, and a link straight to that requirement assessment). **Expand all** / **Collapse all** act on every section at once.
- **Per domain** — pivots the same rows by the domain (Folder) they live in. **Group by domain depth** controls how far down the tree the grouping cuts (`root` … `leaf domain`), and **Sort by** orders the rows by domain name (alphabetical), compliance %, or average score, ascending or descending.

## What gets counted

Only **live** audits roll into the numbers. "Live" means the audit's status is one of:

- `in_progress`
- `in_review`
- `done`

Audits in `planned` or `deprecated` status are visible in the drawer (so you can see them) but **excluded** from the aggregates. The `deprecated` filter exists for a specific reason — when you cut a new audit cycle on the same domain, you mark the previous one deprecated so it doesn't double-count its requirements alongside the new live audit. The page surfaces this rule inline: _"Only assessments with status {statuses} are counted — mark audits as {deprecated} to exclude them."_

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
