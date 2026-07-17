---
description: The shared action-plan surface — applied controls rolled up under an assessment, with budget aggregation, analytics, and exports
---

# Action plans

An **action plan** is the unified view of the [applied controls](../concepts/applied-controls.md) tied to an assessment — sorted, filterable, exportable, and rolled up into a budget overview. It's how the platform turns the long tail of "what we need to do" into a single workable list against one piece of GRC work.

The action plan is **the same surface everywhere** it appears: a table of applied controls with the same columns, the same filters, the same [flash mode](flash-mode.md) entry point, and the same [budget aggregation](#budget-aggregation). What changes is the **assessment** the controls are pulled from.

## Where it appears

The action plan is available on every assessment that aggregates corrective work:

| Assessment | What it pulls | Linked through |
|---|---|---|
| [Audit](../concepts/audits.md) (compliance assessment) | Controls that satisfy the audit's requirements | `requirement_assessments` |
| [Risk assessment](../concepts/risk-assessments.md) | Controls that mitigate the assessment's risk scenarios | `risk_scenarios` |
| [Quantitative risk study](../concepts/quantitative-risk-studies.md) | Controls referenced by the study's quantitative scenarios | quantitative scenarios |
| [Findings assessment](../concepts/findings-assessments.md) (incl. asset assessment) | Controls that remediate the assessment's findings | `findings` |
| [EBIOS RM study](../concepts/ebios-rm.md) | Compliance and risk action plans rolled up across the study | derived report |

In each case the **Action plan** entry sits in the assessment's side menu, on the route `<assessment>/<id>/action-plan`. The list isn't an independent object — it's a live aggregation, so any control you add through the assessment (or anywhere else it gets referenced) shows up here automatically.

## The table

The action-plan table is built on the standard model table, with a column set tuned for "what work is outstanding":

- **Reference ID**, **Name**, **Status**, **Priority**, **Category**, **CSF function**, **Assigned to**, **ETA**, **Expiry date**, **Control impact**, **Effort**, **Annual cost**, plus a context-specific count column (matching requirements / findings / scenarios).
- Default sort is by **ETA** so what's coming up next is at the top.
- All the usual table affordances apply: search, per-column filters, rows-per-page, sort by any column, multi-select for batch actions, right-click for the context menu — see [Working with tables](working-with-tables.md).

The point is that you can drive prioritisation conversations from this page without exporting anything — sort by priority, filter by status, look at what's overdue, reassign to a different owner, all in place.

## Budget aggregation

At the top of every action-plan page sits the **budget overview** — a rolled-up summary of the [annualised cost](../concepts/applied-controls.md#financial-tracking) of every control in the plan, broken down across multiple dimensions:

- **Total annual cost** and **number of controls with cost set**.
- **By status** — how much money is parked behind controls that are _to do_ versus already _active_; useful to see how much of the planned spend has actually been turned on.
- **By priority** — annual cost split across P1 / P2 / P3 / P4, so you can see whether your spend reflects your stated priorities.
- **By category** and **by CSF function** — annual cost grouped by control type (technical / process / physical / …) and by NIST CSF function (Identify / Protect / Detect / Respond / Recover / Govern).
- **By ETA bucket** — overdue / due in 30 days / due in 90 days / later / no ETA.
- **Top assignees** and **top folders** — leaderboard of who and where the cost concentrates, with a status breakdown per assignee.

This view answers two questions at once: _what's the total budget burn for this assessment's remediation_, and _where is it concentrated_. It's also the basis for budgeting conversations with finance — the numbers are derived from the same `cost` field on each applied control, so there's no separate spreadsheet to keep in sync.

{% hint style="info" %}
Costs roll up from each control's [annual-cost calculation](../concepts/applied-controls.md#financial-tracking), which amortises build costs over the configured amortisation period and adds the annual run cost. Controls with no cost set contribute zero to the totals.
{% endhint %}

## Analytics

A dedicated **Analytics** button (on the compliance and risk action plans) jumps to a richer dashboard of the same applied controls — counts and totals broken out as charts rather than the budget summary's compact cards. Use it when you want a presentable visual; use the budget overview when you want the numbers at a glance.

## Flash mode

Every action plan also exposes a **Flash mode** button — a streamlined, keyboard-friendly workflow for creating many applied controls in quick succession against the current assessment. See [Flash mode](flash-mode.md) for the full UX; the assessment is passed through as a filter so newly-created controls land already linked to the audit / risk assessment / findings assessment you launched from.

## Exports

The action plan can be exported for offline review or for handing to stakeholders who don't have platform access:

| Export | Available on |
|---|---|
| **PDF** | Compliance assessment, risk assessment |
| **Excel (`.xlsx`)** | Compliance assessment, risk assessment |
| **CSV** | Compliance assessment |

PDF exports are templated — they include the assessment metadata at the top and the action-plan table styled for print. Excel and CSV exports are the raw control rows, suitable for further work in a spreadsheet.

## Related

- [Applied controls](../concepts/applied-controls.md) — the underlying object and its **financial tracking** mechanics (`build`/`run` cost, amortisation, annual cost).
- [Flash mode](flash-mode.md) — bulk authoring of controls from inside an action plan.
- [Kanban mode](kanban-mode.md) — the visual swim-lane alternative for monitoring the same set of controls by status.
- [Audits](../concepts/audits.md), [Risk assessments](../concepts/risk-assessments.md), [Findings assessments](../concepts/findings-assessments.md), [EBIOS RM](../concepts/ebios-rm.md), [Quantitative risk studies](../concepts/quantitative-risk-studies.md) — the assessments that expose an action plan.
