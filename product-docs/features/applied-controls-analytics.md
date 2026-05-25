---
description: Filter-aware dashboard summarising your applied controls — count, cost, status, priority, ETA, top owners
---

# Applied controls analytics

The **Applied controls analytics** view turns the controls list into a one-page picture: how many controls do we have, how are they spread across status / priority / category / CSF function, what's overdue, who owns the most.

It complements the table — same data, different lens — and respects whatever filters were active on the table when you opened it.

## Where to find it

- **From the controls table** — the chart-pie icon (`Applied controls analytics`) in the toolbar of `/applied-controls`. The filters currently applied to the table are carried over verbatim, so the analytics page reflects the exact slice you were looking at.
- **From an audit's action plan** — each compliance assessment detail page has an `Action plan` sub-route with its own analytics button. Same dashboard, scoped to the controls in that audit's action plan.
- **From a risk assessment's action plan** — same pattern.
- **From an EBIOS RM study's action plan** — same pattern.

When you open the analytics page from the table with active filters, a violet pill above the dashboard reads _"Analytics reflect the filters applied on the table."_ — your reminder that the numbers below are not your whole estate.

## What it shows

The dashboard surfaces several blocks, all computed live from the filtered queryset (no scheduled refresh, no cache):

| Block | What it answers |
|---|---|
| **Total controls** | The headline count for the filtered set |
| **Total annual cost** | Sum of computed annual costs across the filtered set |
| **By status** | Counts and cost per status bucket — To do, In progress, On hold, Active, Degraded, Deprecated, plus "not set" |
| **By priority** | Counts and cost per P1 / P2 / P3 / P4 |
| **By category** | Counts and cost per category |
| **By CSF function** | Counts and cost per Identify / Protect / Detect / Respond / Recover (when set) |
| **ETA distribution** | Five buckets — overdue / due within 30 days / due within 90 days / later / no ETA set |
| **Top owners** (10) | Owners with the most controls; each broken down internally by status |
| **Top domains** (10) | Domains with the most controls |

## Cost computation

Per-control annual cost combines the `build` and `run` blocks from the control's cost JSON:

- `build.fixed_cost / amortization_period` + `(build.people_days × daily_rate) / amortization_period`
- `run.fixed_cost` + `(run.people_days × daily_rate)`

`daily_rate` comes from **Settings → General → Daily rate** (defaults to 500 in the configured global currency). Controls without a `cost` block contribute zero — they're still counted under **Total controls**, just not under **Total annual cost**.

## Other view modes for applied controls

The controls table exposes two alternative views alongside this one:

- **[Flash mode](flash-mode.md)** — flashcards for rapid posture establishment.
- **[Kanban mode](kanban-mode.md)** — drag-and-drop status board with swimlanes per domain.

All three (analytics, flash, kanban) share the same filter passthrough — clicking any of them from the table carries the current filter querystring over.

## Related

- [Dashboards](dashboards.md) — composed metric surfaces built from Metrology widgets
- [Audit advanced analytics](audit-analytics.md) — equivalent dashboard scoped to a single audit
- [Insights](insights.md) — PRO/Enterprise cross-cutting views (impact graph, priority/effort matrix, timeline)
- [Applied controls](../concepts/applied-controls.md)
