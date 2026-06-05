---
description: Cross-cutting analytical views — impact graph, priority/effort matrix, timeline — across the whole estate
---

# Insights

{% hint style="info" %}
**Enterprise (PRO) feature** — ships in the Enterprise edition and is not reachable on the community edition. No feature flag; visibility depends only on edition + the per-view permissions listed below.
{% endhint %}

The **Insights** menu groups three cross-cutting analytical views that don't belong to any single object — they aggregate across all your applied controls and assessments to surface estate-wide patterns.

## Where this sits in the analytical stack

Insights is the **cross-cutting / estate-wide** layer of the platform's advanced analytics. Two more focused layers exist in community for the per-audit and per-framework views:

| Surface | Scope | Edition | Gating |
|---|---|---|---|
| **[Audit advanced analytics](audit-analytics.md)** | One audit | Community | `advanced_analytics` flag |
| **[Framework report](framework-report.md)** | One framework, every live audit using it | Community | None (permission-gated) |
| **Insights** (this page) | Cross-cutting (impact graph, priority/effort, Gantt timeline) | Enterprise (PRO) | None (permission-gated) |

## Where to find it

Sidebar → **Insights**. The group hosts three sub-pages.

## What's in the menu

### Impact analysis

`/insights/impact-analysis` — a force-directed **graph explorer** linking applied controls to the audits, requirements, risk scenarios, and assets they touch. Useful for answering _"if we drop this control, what coverage do we lose?"_ and for spotting controls that carry an outsized share of compliance load.

Underlying endpoint: `/applied-controls/impact_graph/`.

### Priority review

`/insights/priority-review` — an **impact-effort matrix** plotting applied controls on two axes: how much each one would reduce risk (impact) versus how much work it would take to put in place (effort). The classic quadrant chart — do the high-impact / low-effort ones first. Useful for triaging a remediation backlog.

Underlying endpoint: `/applied-controls/impact_effort/`.

### Timeline view

`/insights/timeline-view` — a **Gantt chart** plotting applied controls, compliance assessments, risk assessments, business impact analyses, findings assessments, and security exceptions on a single timeline, with swimlanes by domain.

Controls:

- Toggle each category on/off independently.
- Filter by one or more domains.
- Zoom between weekly / monthly / yearly.
- Optional "use creation date as start" toggle for items without an explicit start date.

It's the answer to _"what's actually on our calendar across all programmes?"_

## Permissions

All three views require: `view_perimeter`, `view_riskscenario`, `view_referencecontrol`, `view_assessment`, `view_riskassessment`. Anyone with those permissions on the Enterprise edition sees the menu.

## Related

- [Audit advanced analytics](audit-analytics.md) — single-audit deep dive (community feature, separate)
- [Applied controls analytics](applied-controls-analytics.md) — applied-controls dashboard with filters
- [Dashboards](dashboards.md)
- [Mapping explorer](mapping-explorer.md) — different graph view (framework-to-framework)
- [Feature flags](../configuration/settings/feature-flags.md)
