---
description: Aggregated view of recurrent tasks completion across time periods
---

# Control Plan

The **Control Plan** is the calendar-style heat-map of your recurrent operational work. Each cell is a task occurrence — colour-coded by status — laid out across time, so a quarter's worth of weekly access reviews or monthly backup tests is visible as one strip. It's the answer to _"are we actually running our recurring controls on cadence?"_

The page is internally `tasks-review` (and the i18n key is `tasksReview`), but the user-facing name everywhere in the UI is **Control Plan**.

## Where to find it

Sidebar → **Control Plan** (under the Overview group). Direct route: `/tasks-review`.

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

## Why "Control Plan" and not "Tasks Review"

The label was renamed: the surface used to be called "Tasks review", which under-sold what it shows. The new name reflects the actual use case — running your control plan, tracking that the operational work behind each control is happening on cadence. The internal `tasksReview` key and the `/tasks-review` URL haven't changed; only the user-facing string did.

## Related

- [Tasks](../concepts/tasks.md) — the template / occurrence model that this page rolls up
- [My assignments](my-assignments.md) — your personal slice of what's due
- [Notifications](notifications.md) — get pinged before a task goes overdue
- [Sync to actions](sync-to-actions.md)
- [Feature flags](../configuration/settings/feature-flags.md)

_Sources: `frontend/src/routes/(app)/(internal)/tasks-review/+page.svelte` — filters at `:68`–`:96`, granularity logic at `:59`–`:65`, status colours at `:105`–`:112`, filter apply / reset at `:114`–`:141`, active-filter badge at `:143`–`:146`, compact-mode toggle at `:16` + header at `:172`. Sidebar entries (label "Control Plan"): `frontend/src/lib/components/SideBar/navData.ts:196` and `enterprise/.../navData.ts:236`. Feature-flag gating: `frontend/src/lib/utils/sidebar-config.ts:5` (`control_plan: boolean`) consumed at `:82` (`tasksReview: featureFlags?.control_plan ?? true`). Labels from `frontend/messages/en.json:3885` (`tasksReview`: "Control Plan"), `:3759` (`controlPlanDescription`)._
