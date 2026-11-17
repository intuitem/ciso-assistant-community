---
description: Filter-aware dashboard over your task definitions — status, due dates, assignees, domains, commitments
---

# Tasks analytics

**Tasks analytics** is to the tasks list what [applied controls analytics](applied-controls-analytics.md) is to the controls list: the same rows, aggregated. It answers *how much operational work is on the books, who holds it, and how much of it is late*.

## Where to find it

- **From the tasks table** — the analytics button (`Tasks analytics`) in the toolbar of `/task-templates`. The filters active on the table are carried over, so the dashboard reflects exactly the slice you were looking at.
- **From an audit's action plan** — scoped to the tasks attached to that audit, its requirements, or a finding raised from one.
- **From a findings binder's action plan** — scoped to the tasks attached to that binder or one of its findings.

When filters are in play, a pill above the dashboard says so. The numbers below are not your whole estate.

## What it shows

| Block | What it answers |
|---|---|
| **By status** | Counts per status of the next occurrence — the same status the table's column shows, so the chart and the list agree |
| **Due dates** | Five buckets — overdue / due within 30 days / due within 90 days / later / no date — matching the applied-control buckets so the two pages read alike |
| **Recurrence** | One-off definitions versus recurring ones |
| **By assignee** | Who holds the most tasks, each broken down by status. Actors you can't see are grouped as *Restricted*; tasks with nobody assigned as *Unassigned* |
| **By domain** | Domains with the most tasks, also broken down by status |
| **Commitments** | With [commitment management](../concepts/commitments.md) on: tasks per commitment state, plus how many have **slipped** and how many are **breached** |

For a recurring definition the status is read from its next *upcoming* occurrence — past ones are skipped — which is what makes "overdue" mean something on a task that has run fifty times.

## Related

- [Tasks](../concepts/tasks.md)
- [Applied controls analytics](applied-controls-analytics.md)
- [Action plans](action-plans.md)
