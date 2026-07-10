---
description: Step-by-step walkthrough for managing an accreditation from start to renewal
---

# Managing an accreditation

An **accreditation** in CISO Assistant tracks a formal authorisation granted to a system, service, or organisation by an authority — typically the outcome of an audit-and-decision process. It captures who granted it, what's in scope, when it expires, and the evidence behind the decision.

See [Project management](../concepts/project-management.md) for how accreditations sit alongside projects and collections.

{% hint style="info" %}
Accreditations live under the **Project management** module. If the sidebar doesn't show it, enable the `project_management` feature flag — see [Feature flags](../configuration/settings/feature-flags.md).
{% endhint %}

## Prerequisites

- The `project_management` feature flag is on.
- _Optional but recommended_: an **entity** with the `accreditation_authority` relationship configured — this is the body issuing the accreditation. You can also type a free-text authority name if the authority isn't registered as an entity.
- _Optional_: a [collection](collections.md) holding the audits, evidences, and exceptions that make up the perimeter you're submitting for accreditation.
- _Optional_: a **checklist** — any [audit](../concepts/audits.md) — used to drive the accreditation's progress bar.

## Create the accreditation

1. From the sidebar, open **Project management → Accreditations**.
2. Click **Start an accreditation**.
3. Fill in the form:
   - **ID** — short reference (e.g. `ACC-2026-001`).
   - **Domain** — folder. Drives IAM scoping.
   - **Author** — the actor preparing the accreditation file (day-to-day owner).
   - **Category** — from your `accreditation.category` [terminology](../concepts/terminology.md). Defaults shipped: _accreditation\_simplified, accreditation\_elaborated, accreditation\_advanced, accreditation\_sensitive, accreditation\_restricted, other_.
   - **Status** — initial status. Defaults shipped: _draft, in\_progress, accredited, not\_accredited, obsolete_.
   - **Collection** — the [collection](collections.md) holding the scope objects (audits, evidences, exceptions, policies, …). The detail page will surface everything in this collection as **Associated objects**.
   - **Authority** — the entity issuing the accreditation. Only entities marked with the `accreditation_authority` relationship appear in the picker. If yours isn't listed, you can register it from **Entities** first.
   - **Custom authority name** — free-text fallback for authorities not registered as entities.
4. _Optional_: expand the **More** dropdown for extended fields:
   - **Checklist** — pick an audit whose progress should drive the accreditation's progress bar.
   - **Commission date** — date the accreditation commission made its decision.
   - **Duration (months)** — accreditation validity. If both **Commission date** and **Duration** are filled in and **Expiry date** is blank on save, CISO Assistant computes the expiry automatically.
   - **Expiry date** — when the accreditation lapses. Manual or auto-computed from the commission date + duration.
   - **Decision evidence** — evidence documents backing the decision (e.g. minutes / _procès-verbal_).
   - **Labels** — filtering labels.
   - **Observation** — free Markdown notes.
5. **Save**.

## Detail page layout

The page comes in two halves:

### Header (from `DetailView`)

Standard detail view with sidebar widgets:

- **Authority** — entity link (or free-text name).
- **Status** and **Category** — colour-coded chips.
- **Checklist** card — clickable; shows the progress percentage from the linked audit. Hidden if no checklist is set.
- **Decision evidence** — list of attached evidences.
- **Validation flows** — if the `validation_flows` feature flag is on, shows current approval status. The header also gains a **Request validation** action.

### Body card

- Top: name, ID.
- Two columns: **Description** and **Observation** (both Markdown).
- **Associated objects** section: a grid of cards, one per category present in the linked collection — audits, risk assessments, CRQ studies, EBIOS RM studies, entity assessments, follow-ups, evidences, exceptions, policies. Each card shows item count, status chips, and a link to the underlying object.

If no collection is linked or the collection is empty, the section shows _"No associated objects in this collection."_

## The four moving parts of an accreditation

Conceptually, the accreditation tracks four things you maintain over time:

1. **The dossier** — _what_ is being accredited. Held in the linked **collection**: the audits, evidences, exceptions, and policies that make up the perimeter. Update the dossier by adding/removing objects in that collection. See [Collections](collections.md).
2. **The progress** — _how far_ the work is. Tied to the **checklist** (an audit). Update the audit, the progress bar follows.
3. **The decision** — _what was decided_. Captured as **Status**, **Commission date**, **Decision evidence**, and the granted **Duration / Expiry date**.
4. **The approval flow** — _who approves the change_. Captured via [validation flows](../introduction/vocabulary.md#v) when the feature flag is on.

## Closing the loop: from draft to accredited

A typical sequence:

1. Create the accreditation with status **draft**, author = you, category set, authority filled in.
2. Build the dossier in the linked collection — pull in the relevant audit (set it as the **checklist** so the progress bar reflects audit completion), add policies, exceptions, and supporting evidences.
3. Move status to **in\_progress** while the commission reviews. The checklist progress bar should climb as the audit progresses.
4. Once the commission decides, set **Commission date**, **Duration**, attach the decision **PV / minutes** as **Decision evidence**, and flip status to **accredited** or **not\_accredited**. The platform auto-computes **Expiry date** from commission date + duration if you leave it blank.
5. _(Optional)_ Trigger a validation flow if your process requires a formal sign-off recorded inside the platform.

## Renewing or retiring

When the expiry date approaches:

- **Renew**: update **Commission date**, **Duration**, and replace **Decision evidence** with the renewal documents. The expiry date recalculates if you blank it.
- **Retire**: move status to **obsolete**. The accreditation stays in history for audit purposes.

## What's next

- [Manage a collection](collections.md) — the dossier behind every accreditation.
- [Audits](../concepts/audits.md) — the typical checklist driving accreditation progress.
