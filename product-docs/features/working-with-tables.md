---
description: One toolbar, everywhere — search, filter, sort, choose columns, and act on rows (single or in bulk) on every model table in CISO Assistant
---

# Working with tables

Almost every list in CISO Assistant — applied controls, risk scenarios, assets, evidences, audits — is a **model table** built from the same component. That means the toolbar and gestures are identical wherever you go: learn them once and they work everywhere.

This page covers the full table surface: the four ways to **shape what you see** (search, filter, sort, columns) and the two ways to **act on rows** (context menu for one, batch actions for many).

## Search

The toolbar's **search box** (placeholder _"Search..."_) runs a full-text search across the table's records. Typing filters the list as you go — the query is debounced, so the table updates a fraction of a second after you stop typing rather than on every keystroke.

Search is scoped to the table you're on and isn't remembered between visits — it's the quick, throwaway way to find a row. For a search that spans the whole platform, use [Universal search](search.md).

## Filtering

The **Filters** button opens a panel of per-column filters tailored to the model — status, domain, owner, priority, labels, and so on. Pick one or more values and the table narrows to matching rows. A small count next to the **Filters** button shows how many filters are active, and **Reset filters** clears them all.

{% hint style="info" %}
**Filters are remembered in your browser, per table.** Set a filter on applied controls, navigate away, come back — it's still applied. The selection is stored locally on standalone list pages, so each table reopens the way you left it.

Two things override a remembered filter: opening the table through a **link that carries filter parameters** (the link's filters win), and embedded sub-tables inside a record's detail page (those don't persist).
{% endhint %}

## Sorting

Click a **column header** to sort by it; click again to flip ascending ↔ descending. An arrow on the header shows the active sort and its direction. Only one column sorts at a time.

### Why some columns aren't sortable

Columns that hold **a list of values per row** — owners, labels, linked threats or assets, applied controls, evidences — have a non-clickable header on purpose. Sorting puts rows in order by a single value, but a cell containing many values has no single value to sort on: ordering rows by a one-to-many or many-to-many relationship is ambiguous and would duplicate rows in the result. Sort by a **scalar column** instead — reference, name, status, a date — and use [Filtering](#filtering) to narrow by the multi-value fields.

## Rows per page and pagination

The **rows-per-page** selector and the page you're on are remembered per table, so a table you like to read 50-at-a-time stays that way.

## Choosing columns

Tables ship with a sensible default set of columns, but the right set depends on the task. The **column selector** — a table-columns icon in the toolbar, next to the rows-per-page control — lets you pick what shows.

The dropdown lists every available column with a checkbox:

- **Tick / untick** to show or hide a column.
- **Show All** reveals everything, including optional columns.
- **Hide All** trims to a single column.
- **Reset to default** returns to the table's standard set.

When some columns are hidden, the button shows a **visible/total** count (e.g. `12/16`).

{% hint style="info" %}
At least one column always stays visible — the last one's checkbox is locked with the note _"At least one column must remain visible"_, so a table can never end up empty. Your column choice is **remembered per table, in your browser**.
{% endhint %}

### Default and optional columns

Two kinds of columns appear:

- **Default columns** — the standard set shown out of the box, visible until you hide them.
- **Optional columns** — extra fields the record already carries but that aren't shown by default, such as **Start date**, **Expiry date**, **Created at**, and **Updated at** on applied controls. They sit at the end of the list, switched off, ready to turn on when you need them.

This keeps default tables clean while putting the less-common fields one click away. Feature-flagged columns switched off for your instance never appear in the list.

## Acting on rows

The same table surfaces two ways to change data without leaving the list: a **context menu** for one row, and **batch actions** for many.

### Context menu — one row

**Right-click any row** to open a shortcut menu. It's the fast path when all you want is to flip one field, skipping the row-detail page.

Three universal items sit at the bottom:

- **Edit** — opens the row in edit mode (hidden for builtin or library-shipped rows, which are read-only).
- **View** — opens the row's detail page.
- **Delete** — appears only when the table allows deletion and the row isn't builtin. Folders use the recursive-delete dialog; everything else a standard confirm.

Some models add domain-specific shortcuts above the trio:

| Model | Custom items |
|---|---|
| **Applied controls** | Change status · Change impact · Change effort · Change priority · Change CSF function · Replace with |
| **Evidences** | Change status |
| **Task occurrences** | Change status |
| **Vulnerabilities** | Change status · Change severity |
| **Elementary actions** (EBIOS RM) | Change attack stage |
| **Feared events / RO-TO couples / Stakeholders / Attack paths / Operational scenarios** (EBIOS RM) | Select object |

The win is speed and staying in context — you keep your scroll position, filters, and selection.

### Batch actions — many rows

When the same change has to land on many rows, models that opt in grow a **leading checkbox column**. Tick rows (or the header checkbox to select the whole page) and a **batch action bar** appears with the operations available on that model.

| Type | What it does |
|---|---|
| **Delete** | Removes the selected objects (skips builtin / library-protected rows) |
| **Change field** | Sets a single scalar field on all selected rows |
| **Change M2M** | _Replaces_ a many-to-many field with the picked values |
| **Add M2M** | _Appends_ values to a many-to-many, keeping existing ones |
| **Remove M2M** | _Removes_ specific values from a many-to-many, keeping the rest |
| **Change folder** | Reassigns the rows' [domain](../concepts/domains.md) |
| **Group** | A submenu bundling related actions under one button |
| **Merge** | Combines selected rows into one (today: applied controls) |

Most actions open a confirmation modal — a count and explicit confirm for **Delete**, a dropdown of valid values for **Change field**, a searchable list for the M2M actions, a domain picker for **Change folder** — so a 200-row change is never an accident. Validation runs through the model's normal write rules, the same ones that protect a single edit.

Batch actions are **opt-in per model**. Applied controls have the richest set; risk scenarios, vulnerabilities, evidences, tasks, assets and others carry subsets. Sensitive surfaces like users, frameworks and folders deliberately ship without bulk actions, and requirement assessments have no bulk delete by design (they're children of audits).

## What's remembered in your browser

Your table preferences are stored **locally, per browser and per device** — they don't follow you to another machine or sync to your account.

| Preference | Remembered? |
|---|---|
| Active **filters** | Yes, per table (a filter-carrying link overrides) |
| **Columns** shown | Yes, per table |
| **Rows per page** and current page | Yes, per table |
| **Search** text | No — clears each visit |
| **Sort** column | No — resets to the table's default each visit |

## Related

- [Universal search](search.md) — search across the whole platform, not just one table
- [Action plans](action-plans.md) — a table view that leans on these affordances
- [Applied controls](../concepts/applied-controls.md) — the model with the richest row actions and optional columns
- [Domains](../concepts/domains.md) — the target of the **Change folder** batch action
