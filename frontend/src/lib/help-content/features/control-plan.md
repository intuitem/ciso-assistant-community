---
description: Aggregated view of recurrent tasks completion across time periods
---

# Control Plan

The **Control Plan** is the calendar-style heat-map of your recurrent operational work. Each cell is a task occurrence — colour-coded by status — laid out across time, so a quarter's worth of weekly access reviews or monthly backup tests is visible as one strip. It's the answer to _"are we actually running our recurring controls on cadence?"_

## Where to find it

Sidebar → **Control Plan** (under the Overview group).

The page is gated by the `control_plan` feature flag, **default on** — so it ships visible in both community and Enterprise editions unless an admin disables it.

## Layout

The body is a grid:

- **Columns** — time periods. Choose **monthly** (default) or **weekly** granularity from the granularity dropdown. The header above the grid shows the selected start → end range.
- **Rows** — task definitions (one row per recurring `TaskTemplate`), grouped by the relevant scope.
- **Cells** — one per occurrence, colour-coded by status:

| Status | Cell colour |
|---|---|
| Completed | Green |
| In progress | Violet |
| Pending | Red |
| Cancelled | Gray |
| No occurrence in this period | Dashed white |

A glance gives you the run rate; clicking a cell jumps into the corresponding task occurrence.

## Filters

A collapsible filter panel above the grid takes:

- **Start period / end period** — month inputs (e.g. `2026-01` to `2026-12`); default is the current year.
- **Granularity** — monthly or weekly.
- **Domain** — narrow to a single folder.
- **Assigned to** — by actor.
- **Applied controls** — narrow to occurrences that maintain a specific control.
- **Status** — filter the rendering by completion state.

The filter button shows an active-filter count badge so you don't lose track of which view you're on. The **Reset** action clears all filters and snaps the period back to the current calendar year.

## Compact mode

A toggle in the header collapses each row's detail to fit more recurring tasks on screen at once — useful when you have dozens of task templates.

## Related

- [Tasks](../concepts/tasks.md) — the template / occurrence model that this page rolls up
- [My assignments](my-assignments.md) — your personal slice of what's due
- [Notifications](notifications.md) — get pinged before a task goes overdue
- [Sync to actions](sync-to-actions.md)
- [Feature flags](../configuration/settings/feature-flags.md)
