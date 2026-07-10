---
description: Filter the entire workspace to a single domain
---

# Focus mode

**Focus mode** scopes the whole application to a chosen domain. While focus mode is active, every list, every dashboard, every count, every search reflects only what lives inside the focused domain (and its sub-folders). Clear the focus to return to "All domains".

It's a viewer-level concern — focus mode never changes anything on the server side, only what each request asks for.

{% hint style="info" %}
Focus mode is gated by the `focus_mode` feature flag. PRO; default off. See [Feature flags](../configuration/settings/feature-flags.md).
{% endhint %}

## Engaging focus

The focus-mode selector lives in the top bar — a crosshair-icon button labelled **All domains** when nothing is focused. Click it to open the picker:

- A searchable tree of every domain you have access to.
- A persistent sort toggle (A→Z / Z→A) when not searching.
- Type to filter — matches are flattened with a breadcrumb path so deeply-nested domains stay reachable.

Pick a domain. The button switches to an indigo pill carrying the domain name, the page reloads scoped to that domain, and every subsequent navigation stays inside the focus until you clear it.

The small **×** on the right of the pill (or the **All domains** entry at the top of the picker) returns you to the unfocused view.

## What stays unfocused

A small allowlist of endpoints is always exempt from focus filtering, because they have to work regardless of which domain you're looking at:

- **Current user** — authentication metadata.
- **CSRF token**, **allauth flows** — login plumbing.
- **License**, **build info**, **global settings** — instance-wide.
- **Pending risk acceptances** — surfaced to approvers across all domains.
- **SSO settings** — admin-level.
- The **folders** endpoint when called with `no_focus=true` — used by the picker itself.

Everything else (assets, audits, risks, controls, dashboards, search results) is filtered to the focused domain and its descendants.

## How focus survives navigation

The chosen focus is persisted in two places:

- A **browser localStorage entry** so it survives reloads.
- A **`focus_folder_id` cookie** that the SvelteKit server reads and forwards as the `X-Focus-Folder-Id` header on every API request.

Server-side, a middleware validates the UUID, stores it on a per-request context variable, and `BaseModelViewSet.get_queryset()` clamps the result to the focused folder. If the feature flag is off, the header is ignored even if a stale cookie is present — turning the flag off everywhere takes immediate effect on the next request.

## When to use it

- **Multi-tenant operators** — managing many client domains from one instance, focused on one client at a time.
- **Large organisations** — when "all of XYZ Corp" is overwhelming and "just my business unit" is what you actually need on a given day.
- **Demos and onboarding** — pre-populate a domain, focus on it, and the rest of the platform vanishes from the demo flow.

{% hint style="warning" %}
**Disable focus mode for admin-level tasks.** The filter applies to almost everything, including admin surfaces like **users and groups**, **libraries**, **roles**, and other settings pages. Working on those while focused can hide objects you'd expect to see (a user in another domain, a library not yet attached to the focused domain) or make changes feel like they're failing silently. Clear the focus before doing admin work, then re-engage it when you're back to day-to-day operations.
{% endhint %}

## Limits

- Focus mode is **per-user** and **per-browser**. There's no way to lock all users of an instance into a single domain through this mechanism — for that, see IAM scoping in [Understanding the IAM model](../configuration/organization/iam-model.md).
- Focus on a domain doesn't grant permissions you don't already have — it only filters what you already had access to.
- A user with no access to the focused domain will see an empty workspace; pick another or clear the focus.
