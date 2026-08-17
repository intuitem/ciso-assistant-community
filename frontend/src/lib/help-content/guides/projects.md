---
description: Step-by-step walkthrough for creating and operating a project, programme, or portfolio
---

# Managing a project

The **Project** object in CISO Assistant is the unit you use to plan and track a piece of work — from a single delivery up to a full portfolio of programmes. Each project records its charter, schedule, financials, people, scope, linked objects, and a rolling analytics history.

See [Project management](../concepts/project-management.md) for how projects sit alongside accreditations and responsibility matrices.

{% hint style="info" %}
Projects live under the **Project management** module. If the sidebar doesn't show it, enable the `project_management` feature flag — see [Feature flags](../configuration/settings/feature-flags.md).
{% endhint %}

## Prerequisites

- The `project_management` feature flag is on.
- _Optional_: a parent project already exists (if you want to slot the new project under a portfolio or programme).
- _Optional_: actors exist for the owner and sponsor you intend to set. See [Actors and teams](../concepts/actors-and-teams.md).

## Project, programme, or portfolio?

Every project carries a **Kind**:

- **Portfolio** — a collection of programmes/projects rolled up for strategic reporting. Portfolios don't expose the **Scope** tab.
- **Programme** — a coordinated set of projects pursuing a common outcome.
- **Project** — the unit of delivery.

Kind is purely an organisational hint — it changes the icon, the colour accent, and (for portfolios) hides the Scope tab. It does not unlock or hide functionality otherwise. You can change it later from the header **Edit** button.

## Create the project

1. From the sidebar, open **Project management → Projects**.
2. Click **Create a project**.
3. Fill in the form:
   - **Kind** — Portfolio, Programme, or Project. Defaults to **Project**.
   - **ID** — an optional short reference (e.g. `PRJ-2026-001`).
   - **Domain** — the folder this project belongs to. Drives IAM scoping.
   - **Assigned to** — the project owner (day-to-day lead). Picks from non-third-party actors.
   - **Status** — initial status from your project-status terminology.
4. **Save**.

The project opens in **Overview** mode, with a card containing the header strip (kind badge, name, ref ID), four KPI tiles (status, health, priority, progress), an info row (owner, sponsor, parent project, sub-projects), and seven content tabs.

{% hint style="info" %}
On creation, CISO Assistant auto-creates a **linked collection** named after the project. That collection is what holds the project's scope objects (assets, audits, risk studies, etc.); you'll see it referenced in the **Linked** tab. You can swap it for a different collection later.
{% endhint %}

## The detail page at a glance

The detail page is structured as one card with several editable sections. Each section has its own **Edit** button — you can only edit one section at a time. Sections without an Edit button are display-only roll-ups.

| Area | What's there | Edit button |
|---|---|---|
| **Header strip** | Kind badge, name, ref ID, ref link, description | Hover the title → small pen icon |
| **KPI tiles** | Status, Health, Priority, Progress | Edit on the **Overview** tab |
| **Info row** | Owner, Sponsor, Parent project, Sub-projects | Owner/Sponsor on **People** tab; Parent on **Header** |
| **Overview tab** | Status, Health, Priority, Progress | ✅ |
| **Charter tab** | Purpose, Objectives, Success criteria, Business case, Approval requirements, Exit criteria, Organisational alignment | ✅ |
| **Tracking tab** | Schedule (start/end/ETA/closed), Financials (budget/actual/currency), Tolerances | ✅ |
| **Scope tab** _(not on Portfolios)_ | Deliverables, Assumptions, Constraints, Dependencies | ✅ |
| **Linked tab** | Linked collection, Responsibility matrices, Labels | ✅ |
| **People tab** | Owner, Sponsor | ✅ |
| **Analytics tab** | KPI cards + lifecycle / progress / financials charts over time | Read-only |

The **Save** / **Cancel** buttons are at the top right of each tab while editing.

## Set the high-level state (Overview)

The Overview tab is where you keep the lifecycle KPIs current:

- **Status** — from your `project.status` [terminology](../concepts/terminology.md). Defaults shipped: _draft, initiated, planning, in\_progress, on\_hold, closing, closed, cancelled_.
- **Health** — `project.health` terminology. Defaults: _green, amber, red_.
- **Priority** — **P1** (highest) to **P4** (lowest).
- **Progress** — 0–100% slider, in steps of 5.

{% hint style="info" %}
**Closing the project**: when you change the status to the built-in `closed`, CISO Assistant auto-stamps **Closed at** with today's date. Moving the status back out of `closed` clears that date.
{% endhint %}

## Fill in the charter

The **Charter** tab is a stack of free-form Markdown fields:

- **Purpose** — why the project exists.
- **Objectives** — what it must achieve.
- **Success criteria** — how you'll know it succeeded.
- **Business case** — the value rationale.
- **Approval requirements** — who must sign off, on what, when.
- **Exit criteria** — what defines "done".
- **Organisational alignment** — how it ties to strategy / parent programme.

Click **Edit** to expand all fields into Markdown editors, fill them in, then **Save**.

## Plan dates, budget, and tolerances (Tracking)

The **Tracking** tab is split into three sections.

### Schedule

- **Start date** / **End date** / **ETA** — calendar pickers.
- **Closed at** — read-only; auto-set when the status moves to `closed`.

### Financials

- **Expected budget** and **Actual cost** — decimals. Currency picker uses ISO codes (e.g. `EUR`, `USD`, `JPY`).
- A live progress bar in view mode shows `actual / expected` as a percentage, **green** below 80%, **amber** between 80–100%, **red** above 100%.
- **Remaining** is computed (`budget − actual_cost`) and turns red when negative.

When you create the project, the currency defaults to its parent project's currency, then to the global setting if there's no parent.

### Tolerances

Tolerances are pre-agreed margins. Exceeding any one of them is a signal that the project should be escalated. Fields:

| Field | Format |
|---|---|
| **Time** | `+ Days`, `− Days` (integers, ≥ 0) |
| **Cost** | `+ %`, `− %` (decimals, ≥ 0) |
| **Scope**, **Quality**, **Benefits**, **Risk** | Free-form text |

When **not** in edit mode, only the dimensions you've filled in are shown.

## Describe deliverables and constraints (Scope)

The **Scope** tab is hidden for Portfolios. For Programmes and Projects it holds four Markdown fields:

- **Deliverables** — what the project must produce.
- **Assumptions** — what's being taken as given.
- **Constraints** — fixed limits (budget, deadlines, regulatory).
- **Dependencies** — external work the project depends on.

Edit / save model is the same as Charter.

## Attach the project's scope (Linked)

The **Linked** tab is how a project connects to the rest of the platform:

- **Linked collection** — the [Generic collection](../concepts/project-management.md) that holds this project's objects. Auto-created on project creation; can be swapped later.
- **Responsibility matrices** — one or more [responsibility matrices](responsibility-matrix.md) you want to apply to this project.
- **Labels** — filtering labels for cross-cutting reporting.

## Assign owner and sponsor (People)

- **Assigned to (Owner)** — _Day-to-day project lead._ Selected from non-third-party actors.
- **Sponsor** — _Executive sponsor; owns the business case._ Same actor pool.

Both fields are independent of IAM permissions; they're descriptive only.

## Read the analytics (read-only)

The **Analytics** tab is generated from automatic project snapshots — CISO Assistant records a `BuiltinMetricSample` each time you save a project, building a time series of its lifecycle. You'll see:

- Four KPI tiles for the latest snapshot (Progress, Status, Health, Actual cost), with a **vs 7d ago** delta for Progress.
- A **Lifecycle — Timeline** chart stacking Status, Health, and Priority over time.
- Progress and Financials line charts.

If no snapshots exist yet (the project was just created), the tab shows _"No analytics data yet."_ Snapshots accrue as you edit the project over time.

## Nest projects (Parent / Sub-projects)

Use the **Parent project** picker (in the header edit form) to slot a project under another. The parent picker shows kind prefixes (`portfolio | programme | project`) and the parent's domain to help you navigate.

- Sub-projects appear as chip links in the info row of the parent's detail page.
- A project can have at most one parent.
- Currency on a new project defaults to the parent's currency.

A typical hierarchy: **Portfolio → Programme → Project** (with sub-projects under it as needed).

## What's next

- [Manage a responsibility matrix](responsibility-matrix.md) and attach it via the **Linked** tab.
- Use the project's [generic collection](../concepts/project-management.md) to bundle the assets, audits, risk studies, and tasks that fall in scope.
- Track lifecycle drift on the **Analytics** tab — `status` going amber/red, ETA slipping past tolerances, or actual cost crossing budget thresholds.
