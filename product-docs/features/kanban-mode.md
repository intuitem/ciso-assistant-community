---
description: Drag-and-drop status board for applied controls, with swimlanes per domain
---

# Kanban mode

**Kanban mode** lays out the applied controls as a status board — one column per status, one row (swimlane) per domain. It's the view to reach for when you're driving execution: moving controls forward visually and spotting which domain is sitting on the most "in progress" work.

## Where to find it

Open the controls table (`/applied-controls`) and click the **table-columns icon** in the toolbar, next to the flash-mode and analytics buttons. The active table filters are carried over.

Kanban mode is currently only available for applied controls.

## Layout

- **Columns** — one per status: `--` (unset), To do, In progress, On hold, Active, Degraded, Deprecated. The column header shows a running count of controls in that status across all swimlanes.
- **Swimlanes** — one per domain. Each swimlane can be collapsed or expanded; the swimlane header shows the per-domain count.
- **Cards** — one per control. Each card shows name, priority badge (P1–P4 with colour), owner initials, and ETA (highlighted red when overdue, except for `active` or `deprecated` controls which are never flagged overdue).
- **Compact mode** — a toggle in the page header reduces card detail to fit more controls on screen.

## Moving cards

Drag a card to a different **status column** to update its status — the change is saved immediately. Drag a card to a different **swimlane** to reassign its domain.

## Other view modes for applied controls

- **[Applied controls analytics](applied-controls-analytics.md)** — chart-pie dashboard with counts, cost, ETA buckets, and top owners.
- **[Flash mode](flash-mode.md)** — flashcards for rapid posture establishment.

All three share the same filter passthrough from the table.

## Related

- [Applied controls](../concepts/applied-controls.md)
- [Sync to actions](sync-to-actions.md) — how controls flow into the action plan from assessments
