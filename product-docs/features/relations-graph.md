---
description: Explore what an object is linked to, as a graph you expand hop by hop
---

# Relations graph

The **relations graph** answers _"what is this linked to?"_ without opening tab after tab. It draws the object in the middle and everything linked to it around it — the risk scenarios a control mitigates, the requirements it satisfies, the assets and evidences behind it — and lets you walk from there.

## Turn it on

It is off by default. An administrator turns on the **Relations graph** [feature flag](../configuration/settings/feature-flags.md): _Show a Relations button on supported detail pages, opening a graph of what the object is linked to._

The button shows on the detail pages of **applied controls**, **risk scenarios**, **assets** and **documents**.

## Explore

Click **Relations graph** on the detail page. A drawer opens with the object and its direct links, grouped by relation.

- **Click** a linked object to expand its own links, and again to collapse them. **Expand all** opens the next level for up to ten objects at once.
- **Open the object page** on a selected object jumps to it.
- The graph goes **3 hops** from the starting object and holds up to **100 objects**. Past either limit it tells you so: open that object's page to explore from there, or collapse a branch first.
- **Per relation** sets how many objects to draw per relation (5 by default) before the rest collapse into a `+N` node; click it to open them.
- **Filter by type** hides kinds of objects you don't need; **Toggle labels** and **Toggle width** (**Widen** / **Narrow**) adjust the view.
- **Start over** collapses everything, restores the filters and reloads.

The graph only shows objects you are allowed to view.

## Related

- [Applied controls](../concepts/applied-controls.md)
- [Risk assessments](../concepts/risk-assessments.md)
- [Assets](../concepts/assets.md)
- [Documents](../concepts/documents.md)
