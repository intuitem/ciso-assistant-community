---
description: Step-by-step walkthrough for creating and operating a responsibility matrix
---

# Managing a responsibility matrix

A responsibility matrix maps **activities × actors → roles** so a project, programme, or operating procedure has a clear answer to "who does what" at every step. CISO Assistant supports three taxonomies — **RACI**, **RASCI**, and **RAPID** — and lets you bind each activity to assets, controls, audits, and other GRC objects.

See [Project management](../concepts/project-management.md) for how matrices sit alongside projects and accreditations.

{% hint style="info" %}
Responsibility matrices live under the **Project management** module. If the sidebar doesn't show it, enable the `project_management` feature flag — see [Feature flags](../configuration/settings/feature-flags.md).
{% endhint %}

## Prerequisites

- The `project_management` feature flag is on.
- You have at least one **actor** to assign — actors wrap users, teams, or entities. Create a user, a team, or an entity first if none exist yet. See [Actors and teams](../concepts/actors-and-teams.md).
- _Optional_: the project you want to attach the matrix to already exists.

## Create the matrix

1. From the sidebar, open **Project management → Responsibility matrices**.
2. Click **Create a responsibility matrix**.
3. Fill in the form:
   - **ID** — an optional short reference (e.g. `RAM-01`).
   - **Domain** — the folder this matrix belongs to. Drives IAM scoping.
   - **Preset** — pick the taxonomy:
     - **RACI** _(default)_ — **R**esponsible, **A**ccountable, **C**onsulted, **I**nformed.
     - **RASCI** — RACI plus **S**upport.
     - **RAPID** — Bain's decision-making model: **R**ecommend, **A**gree, **P**erform, **I**nput, **D**ecide.
   - **Labels** — optional filtering labels.
4. **Save**.

{% hint style="warning" %}
The preset is **locked once the matrix exists**. Switching taxonomies later means starting a new matrix.
{% endhint %}

The matrix opens with the roles for that preset pre-attached. The page loads in **view mode** (read-only) — you'll see the header showing `0 Activities · 0 Actors · 0/0 cells filled` and an empty-state hint: _"This matrix is empty — Add an actor on the right, then add activities below."_

## Switch to edit mode

The matrix opens read-only on every load to avoid accidental edits. To make any change — add an actor, add an activity, fill a cell, rename anything — click the **Edit** button in the top right of the matrix card. The button turns into **Done**; click it again when you're finished.

All cell, activity, and actor changes auto-save while you're in edit mode — there is no separate save button on the matrix workspace.

## Add actors

In edit mode, the header shows an **Add actor…** dropdown to the left of the **Done** button.

1. Pick an actor from the dropdown — only actors not already on the matrix are listed.
2. Click the **→** button next to the dropdown to attach them.

The actor becomes a new column. Already-attached actors are hidden from the picker, so you can't add the same actor twice.

## Add activities

In edit mode, the last row of the table is an input labelled **Add an activity…**.

1. Type the activity name.
2. Press **Enter**.

The activity appears as a new row at the bottom of the table.

## Assign roles (cell cycling)

CISO Assistant uses a click-to-cycle model — there is no per-cell role dropdown:

- **Click** an empty cell → assigns the **first role** of the preset (R for RACI/RASCI, R for RAPID).
- **Click again** → cycles to the next role (RACI: R → A → C → I → empty → R …).
- **Shift-click** → cycles **backward** through the same sequence.

The legend at the bottom of the matrix lists each role with its colour and a live count of how many cells currently hold it.

## Activity details

Each activity row has a small **info** icon next to its name. Click it to open the **Activity details** drawer on the right. The icon dims when no details are attached and highlights once any are added.

In the drawer you can:

- Edit the **Description** in Markdown — saves on blur.
- Link the activity to other GRC objects (each link section auto-saves on change):
  - **Assets** — what the activity touches.
  - **Applied controls** — controls that realise it.
  - **Tasks** — task definitions that recur from it.
  - **Risk assessments**, **Audits**, **Follow-ups** — assessments it ties into.
  - **Business Impact Analyses** — BIAs that depend on it.

## Reorder activities and actors

Hover an activity row in edit mode — a **grip** handle appears on the left of the row. Drag it up or down to reorder. Drag an actor column header the same way to reorder columns. Reordering persists immediately.

## Remove an activity or an actor

- **Remove an activity**: hover the row and click the trash icon on the right. A confirmation modal asks before deleting.
- **Remove an actor**: hover the column header → click the **×** that appears in its top-right corner. The confirmation modal warns _"Existing cells for this actor will be cleared."_ if any roles were assigned to them.

## Attach the matrix to a project

A matrix lives independently in the catalog — it isn't tied to a project by default. To use it on a project:

1. Open the **Project** detail page.
2. Switch to the **Linked** tab and click **Edit**.
3. In the **Responsibility matrices** picker, select the matrix (or matrices).
4. Click **Save**.

The matrices then appear as links on the project page. One matrix can be attached to several projects, and one project can pull from several matrices.

## What's next

- Use the matrix to drive ownership when creating tasks, applied controls, and audits.
- See [Project management](../concepts/project-management.md) for how responsibility matrices sit alongside projects and accreditations in the broader programme view.
