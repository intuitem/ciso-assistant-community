---
description: Select multiple rows in a model table to delete, change fields, edit M2Ms, reassign domains, or merge — in bulk
---

# Batch actions

When the same change has to land on many rows — flipping fifty applied controls to a new owner, retagging a stack of evidences, moving a batch of controls into a new domain — opening each row one by one is busy work. **Batch actions** let you select rows on a model table and apply a bulk operation in one round-trip.

It's the multi-row counterpart to the [Context menu](context-menu.md) (single row).

## How to open it

On any model that supports batch actions, the table grows a **leading checkbox column**. Tick rows to select them; a **batch action bar** appears once the selection is non-empty, with a button for each action available on this model.

A header checkbox selects every row on the current page in one click.

If a model has no batch actions defined, the checkbox column is hidden — the absence is intentional. Sensitive surfaces like `users`, `frameworks`, `folders` are deliberately opt-out by default and don't ship with bulk actions.

## Action types

The platform supports eight action types, all routed through one backend endpoint (`POST /<model>/batch-action`):

| Type | What it does | When you'd use it |
|---|---|---|
| **delete** | Removes the selected objects (skips builtin and URN-protected rows) | Cleaning up a soft-launch backlog |
| **change_field** | Sets a single scalar field on all selected rows | Bulk status flip — e.g. To-do → In progress |
| **change_m2m** | _Replaces_ a many-to-many field with the picked values | Reassigning owner to a single team |
| **add_m2m** | _Appends_ values to a many-to-many without removing existing ones | Tagging a stack of controls with a new label, keeping prior labels |
| **remove_m2m** | _Removes_ specific values from a many-to-many, keeping the rest | Retiring an outdated label |
| **change_folder** | Reassigns the row's domain (FK to `Folder`) | Moving controls to a reorganised domain hierarchy |
| **group** | A nested submenu of related actions | "Change attributes" → status / priority / CSF function under one button |
| **merge** | Combines selected rows into one (currently shipped for applied controls) | Deduping near-duplicates |

For `change_field` and `change_m2m`, validation goes through the model's normal write serializer — so the same business rules that protect a single edit also protect the batch one.

## Per-row exclusions

Some rows are immune to specific actions:

- **Builtin** or **URN-protected** rows (library-shipped reference controls, threats, terminologies) are skipped on `delete` rather than failing the whole batch.
- For `change_folder`, models whose folder is forced by a parent on save (e.g. risk scenarios, where `folder` derives from `risk_assessment.folder`) **don't expose the action** — the change would be silently overwritten.

## Where it's available

Batch actions are strictly **opt-in per model**. Today's footprint includes (non-exhaustive): applied controls (the richest set — status, priority, CSF function, owner, labels, folder, merge), risk scenarios, vulnerabilities, evidences, requirement assessments (no delete by design — they're children of audits), tasks, assets, and several others.

Adding batch actions for a new model is a frontend-only change: add an entry to `batchActions` in `table.ts`. No backend change is needed for the standard action types — the model's existing serializer handles validation.

## Confirmation flow

Most batch actions open a confirmation modal so you don't move 200 rows by accident:

- **delete** shows a count and an explicit confirm.
- **change_field** shows a dropdown of valid values.
- **change_m2m / add_m2m / remove_m2m** show a searchable checkbox list.
- **change_folder** shows a domain picker (filtered to domain-like folders, not root or special folders).

## Related

- [Context menu](context-menu.md) — the single-row sibling
- [Applied controls](../concepts/applied-controls.md) — the model with the broadest batch-action coverage
- [Domains](../concepts/domains.md) — the target for `change_folder`
