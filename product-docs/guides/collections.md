---
description: Step-by-step walkthrough for building and curating a collection
---

# Managing a collection

A **collection** is a hand-curated bundle of GRC objects — audits, risk studies, evidences, policies, exceptions — grouped under a single name. It's the building block CISO Assistant uses for "scope" wherever scope matters: a project's perimeter, an accreditation's evidence pack, or any custom roll-up you want to query as a unit.

See [Project management](../concepts/project-management.md) for how collections, projects, and accreditations fit together.

{% hint style="info" %}
Collections live under the **Project management** module. If the sidebar doesn't show it, enable the `project_management` feature flag — see [Feature flags](../configuration/settings/feature-flags.md). The internal model name is `GenericCollection`, but the UI just says "Collection".
{% endhint %}

## What a collection holds

A collection is a thin envelope around nine many-to-many relationships. Anything in CISO Assistant that can live in a project's scope can sit inside a collection:

- **Audits** (`compliance_assessments`)
- **Risk assessments**
- **CRQ studies** (quantitative risk)
- **Ebios RM studies**
- **Entity assessments** (third-party)
- **Follow-ups** (`findings_assessments`)
- **Documents** — evidences attached to the collection
- **Exceptions** — security exceptions
- **Policies**

A collection itself carries only an **ID**, a **Domain**, **labels**, an **observation**, and the relationships above. It has no status, lifecycle, or schedule — those belong to the objects inside it.

{% hint style="info" %}
Creating a project auto-creates a collection named after it, then links it as the project's **linked collection**. So every project ships with a ready-to-fill scope envelope.
{% endhint %}

## Prerequisites

- The `project_management` feature flag is on.
- You know roughly what you want to scope — a project, an accreditation perimeter, a regulatory bundle, etc.

## Create a collection

1. From the sidebar, open **Project management → Collections**.
2. Click **Create a collection**.
3. Fill in the form:
   - **ID** — optional short reference (e.g. `COL-2026-Q1`).
   - **Domain** — the folder this collection belongs to. Drives IAM scoping.
   - **Labels** — optional filtering labels.
   - **Relationships** (dropdown) — pre-attach existing objects in any of the nine categories above. You can also defer this and add objects from the detail page once the collection exists.
4. **Save**.

## Curate from the detail page

The collection detail page has two parts:

- **Header** (from `DetailView`) — name, ID, domain, labels, observation, the standard Edit/Delete/Duplicate actions.
- **Tabbed area** below the header — one tab per relationship category that has at least one related-model entry. Tabs are sorted alphabetically.

Each tab is a filtered table of the objects in that category — same columns and behaviour as the standalone list page, but scoped to this collection.

### Two ways to attach objects

Each tab has a pair of compact buttons at the top right:

| Button | Icon | What it does |
|---|---|---|
| **Select** | hand-pointer (☝) | Opens a modal listing _existing_ objects of that type; pick one or many to attach to this collection. |
| **Add** | file-circle-plus (📄+) | Opens the standard creation modal for that type, pre-scoping the new object to this collection. |

Use **Select** when the object already exists in the platform and you just want to pull it into the scope. Use **Add** when you need to create it from scratch.

Removing objects is done from the object itself, not from the collection page — open the linked object's detail page and detach it (the collection table on this page hides the bulk-delete affordance to avoid accidentally deleting the referenced objects).

## Reuse a collection

Because a collection is just a bag, you can point several objects at the same collection. The most common patterns:

- **Project scope**: the project's `linked_collection` is the canonical place to grow the project perimeter. Most teams keep one collection per project.
- **Accreditation perimeter**: an [accreditation](accreditations.md) links to one collection holding the audits, evidences, and exceptions that justify it. The accreditation detail page surfaces all of them as **Associated objects**.
- **Custom roll-ups**: a regulator pack, a board report bundle, a "things in flight this quarter" envelope. Spin up a fresh collection and stuff what's relevant.

A single object (an audit, an evidence, a policy) can appear in more than one collection — the M2M relationships are independent.

## Observation field

The **Observation** field is a free-form Markdown note attached to the collection — useful for documenting why this bundle exists, who curated it, and any caveats. It's not shown on the list page, only on the detail page.

## What's next

- [Manage a project](projects.md) — the most common consumer of a collection.
- [Manage an accreditation](accreditations.md) — uses a collection as the evidence perimeter.
