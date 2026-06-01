---
description: Cross-audit aggregate for one framework — compliance %, average implementation score, in-scope audits, status breakdown
---

# Framework report

The **Framework report** is the answer to _"how is this framework doing across our organisation?"_ Pick any framework loaded into the platform, and the report rolls up every audit using it into a single view: compliance percentage, average implementation score, sections breakdown, and the full list of audits in scope.

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
| **Implementation-group filter** | Narrow the report to a single IG via query param |

## What gets counted

Only **live** audits roll into the numbers. "Live" means the audit's status is one of:

- `in_progress`
- `in_review`
- `done`

Audits in `planned` or `deprecated` status are visible in the drawer (so you can see them) but **excluded** from the aggregates. The `deprecated` filter exists for a specific reason — when you cut a new audit cycle on the same domain, you mark the previous one deprecated so it doesn't double-count its requirements alongside the new live audit. The page surfaces this rule inline: _"Only assessments with status {statuses} are counted — mark audits as {deprecated} to exclude them."_

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
