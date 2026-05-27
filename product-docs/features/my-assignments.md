---
description: Personal cross-cutting dashboard listing everything you (or your teams) own across the platform
---

# My assignments

**My assignments** is a personal dashboard listing every object across the platform where _you_ are owner, author, assignee, or approver. It's the answer to "what's on my plate today?" without trawling through each module.

## Where to find it

In the sidebar, under the **Overview** group: **Assignments** (link: `/my-assignments`).

## What it surfaces

The page is a grid of buckets — one per category. Each card shows the count for that category and a filtered table of the actual objects. Empty categories are hidden by default; toggle **Show empty sections** to reveal them.

Categories surfaced (in render order):

| Category | What's listed | Match rule |
|---|---|---|
| **Applied controls** | Controls you own | `owner` |
| **Tasks** | Task definitions assigned to you | `assigned_to` |
| **Audits** | Audits where you're an author or reviewer | `authors` |
| **Risk assessments** | Risk assessments where you're an author or reviewer | `authors` |
| **Risk scenarios** | Scenarios you own | `owner` |
| **Incidents** | Incidents you co-own | `owners` |
| **Exceptions** | Security exceptions you co-own | `owners` |
| **Follow-ups** | Findings assessments where you're an author | `authors` |
| **Findings** | Findings you own | `owner` |
| **Validation flows** | Approval requests waiting for you | `approver` _(user, not actor)_ |
| **Organisation objectives** | Objectives assigned to you | `assigned_to` |
| **Right requests** | Privacy right requests you own | `owner` |
| **Metric instances** | Metric instances you own | `owner` |

Above the grid, an **activity tracker** widget summarises across categories — counts and progress at a glance.

## Direct vs through-team assignments

Most match rules use the **actor** abstraction — and an actor wraps a user, a team, or an entity. So "your assignments" can mean different things:

- **Direct assignments only** _(default)_ — only items where _your user actor_ is on the field.
- **Include team assignments** — also list items where _any team you belong to_ is on the field. Use this to see work that's queued for any team you're part of, even if it's not assigned to you personally.

The toggle button in the top right switches between the two modes. The backend resolves the actor list via `Actor.get_all_for_user(user)`: it walks team memberships (member, leader, deputy) and returns every actor that maps to you.

Validation flows are the one exception — their `approver` is a **User** foreign key, not an Actor. The page wraps that automatically: when filtering by team, all team members' user IDs are added to the approver filter.

## Filter by actor _(PRO)_

The Enterprise edition adds a **Filter scope** picker above the grid. It lets a privileged user re-target the dashboard to any actor.

Who can use it:

- Users with the **Administrator** role.
- Users with the **Domain manager** role.

How it works:

1. Expand the **Filter scope** dropdown.
2. Switch the radio from **Current user** to **Filter by actor**.
3. Pick one or several actors in the search box.
4. Click **Apply**.

The page header keeps showing **Assignments** but appends the picked actor names — e.g. _Assignments - Jane Doe, Compliance Team_ — so it's clear you're looking at someone else's dashboard. Switch back to **Current user** to return to your own view.

Combine with the **Include team assignments** toggle to broaden each picked actor's view through their team memberships.

## Empty sections

The page hides categories with zero items by default to keep the surface scannable. Toggle **Show empty sections** to render every category card — useful when you want to confirm "no, I really have no incidents".

## How counts and tables relate

The page fetches counts first (cheap aggregate query per category), then each table loads independently. So you'll see badge counts populate fast, while individual tables paint as their data lands. If a category exceeds typical bucket sizes (e.g. you own hundreds of applied controls), the embedded table is paginated like any other model table.

## What's next

- [Actors and teams](../concepts/actors-and-teams.md) — the actor model and how team membership resolves to assignments.
- [Dashboards](dashboards.md) — the sibling surface for composed metric views.
- [Notifications](notifications.md) — push-style alerts when an assignment changes hands or approaches its due date.
