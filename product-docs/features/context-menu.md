---
description: Right-click any row on a model table for shortcut actions — edit, view, delete, plus per-model field changes
---

# Context menu

Every model table in CISO Assistant supports **right-click** on a row to open a context menu — a shortcut surface that skips the row-detail page when all you want to do is flip one field. It's the single-row counterpart to [Batch actions](batch-actions.md).

## How to open it

Right-click anywhere on a row in any model table — the table-level UI is shared across the platform, so the gesture works the same way everywhere.

## Default items

Three universal items appear at the bottom of the menu:

- **Edit** — opens the row in edit mode. Hidden when the row is **builtin** or carries a **URN** (e.g. library-shipped reference controls, threats, terminologies — for those the menu still appears, but only with `View` and any model-specific items).
- **View** — opens the row's detail page (read-only).
- **Delete** — appears only when the table provides a delete form and the row is not builtin/URN. Folders prompt with the recursive-delete dialog; everything else uses the standard confirm modal.

If none of the three would appear and the model has no custom actions either, the context menu doesn't render — no empty popup.

## Per-model custom items

Some models add domain-specific shortcut actions above the default trio. Today's registry:

| Model | Custom items |
|---|---|
| **Applied controls** | Change status · Change impact · Change effort · Change priority · Change CSF function · Replace with |
| **Evidences** | Change status |
| **Task occurrences** | Change status |
| **Vulnerabilities** | Change status · Change severity |
| **Elementary actions** (EBIOS RM) | Change attack stage |
| **Feared events / RO-TO couples / Stakeholders / Attack paths / Operational scenarios** (EBIOS RM) | Select object |

Adding a custom item for a model is a frontend change — add a component to the `contextMenuActions[urlmodel]` registry; the action then renders for every row of that model wherever its table is shown.

## Why use it over the row page

- **Speed** — a status flip from To-do → In progress is one right-click away, no page navigation, no scroll-down-to-the-status-field.
- **Stay in context** — you keep your scroll position, your filters, and your selection.
- **Bulk paths** — when you want the same change on _many_ rows, use [Batch actions](batch-actions.md) instead. Context menu is for one row.

## Related

- [Batch actions](batch-actions.md) — the multi-row sibling
- [Applied controls](../concepts/applied-controls.md), [Vulnerabilities](../concepts/vulnerabilities.md), [Evidence](../concepts/evidence.md), [Tasks](../concepts/tasks.md) — the models that ship custom shortcut actions today
