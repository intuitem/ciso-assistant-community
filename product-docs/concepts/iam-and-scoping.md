---
description: How IAM, the domain hierarchy, publication, and cross-domain visibility shape what each user sees
---

# IAM and scoping

This page is the **mental model** for how access and visibility work in CISO Assistant. The full configuration-side deep-dive (SAML / OIDC / MFA / PATs / accounting) lives in [Understanding the IAM model](../configuration/organization/iam-model.md); this page focuses on the three things every user needs internalised before they can predict what they will and won't see on screen:

1. Almost everything is bound to a **domain**.
2. Permissions are inherited **down the domain tree**.
3. Some objects are **published** — visible across the tree — and assessments are not.

The combination of these three is what produces the most common "why am I seeing items from another domain here?" moment, which the last two sections explain and resolve.

## Everything is bound to a domain

The platform's primary scoping unit is the **domain** (see [Domains](domains.md)). Almost every operational object you create carries a domain — that's what drives _who can see it_ and _how it rolls up in reports_.

The list is long on purpose — to make the model concrete:

- **Compliance**: audits / compliance assessments, requirement assessments, evidences.
- **Risk**: risk assessments, risk scenarios, quantitative risk studies, EBIOS RM studies, business impact analyses, security exceptions.
- **Operations**: applied controls, policies, tasks, incidents, findings, findings assessments.
- **Assets**: assets, contracts, entities, solutions, representatives.
- **Privacy**: processings, personal-data inventories, right requests, data breaches.
- **Project management**: projects, accreditations, responsibility matrices.

A small number of objects don't carry a domain because they're either system-wide (the user catalogue, the role catalogue, instance settings) or imported from a library catalogue. Everything else lives _inside_ a domain.

## Inheritance — roles flow down the tree

The domain hierarchy is not just for organising the UI — it actively shapes access. **A role granted on a domain applies to every domain beneath it.** Give a user the _Analyst_ role on a parent domain, and they get analyst-level access to every sub-domain underneath, without re-assigning them at each level.

This is why the tree shape matters as much as the names: putting "France" and "Germany" under a "EMEA" parent isn't decorative — it's the lever that lets EMEA-level managers see across both without granting them individual roles per country.

Permissions only flow **downward**: a role on a sub-domain does _not_ grant any access to the parent. If you need a role-holder to see across siblings, the role goes on the shared ancestor.

The same inheritance also drives reporting: most dashboards and analytics roll up across a domain _and_ its descendants, so a leadership-level view on the parent domain is automatically the consolidated view across its sub-tree.

## Publication — why catalogues appear across all domains

Some objects exist to be **shared**. Frameworks, threats, risk matrices, reference controls, and other catalogue-style items wouldn't be useful if they were trapped in a single domain — every team needs to be able to pull from the same shared library.

CISO Assistant models this through a built-in flag — **`is_published`** — that any object can carry. An object marked as published is visible inside every sub-domain of its own domain, _as if it had been attached to each one_. Publication is a **visibility** mechanism only; it does not let users in other domains create, update, or delete the object.

By default:

- **Catalogue-style objects** (frameworks, threats, matrices, reference controls, libraries, terminologies, …) are published — they live "above" individual domains and are intended to be reused.
- **Assessments** (audits, risk assessments, BIAs, entity assessments) are **not published** — they belong to a specific domain and stay there.

The most common surprise this creates is when a user opens the platform and sees a library of frameworks or threats they "shouldn't" have access to. They aren't seeing them through a permissions hole — they're seeing them because the catalogue is published from a domain that sits above theirs.

If you want to keep a specific object _out_ of the published view, the simplest trick is to attach it to a leaf sub-domain (a domain with no children) — nothing inherits from a leaf.

## Why you sometimes see items from other domains

Assessments routinely _compose_ objects across the tree. Risk assessments reference applied controls, threats, and assets; audits reference applied controls and evidences; findings assessments reference applied controls and the requirement assessments they remediate.

When you're working inside one assessment, the platform's selectors and pickers don't just show you what's in the assessment's own domain — they show you **everything you have access to**. So a risk scenario authored inside the _France_ domain can pull in:

- A shared applied control attached to the _EMEA_ parent domain (you can see it because of inheritance).
- A threat from the global library (you can see it because it's published).
- An asset attached to a sibling _Germany_ domain (if your role gives you access there).

This is by design — composing across the organisation is the whole point of a centralised GRC platform — but it can be disorienting on day one. The rule is consistent: you see what you have access to, regardless of which domain you started on.

## Managing the noise — focus mode (PRO)

When you have access to many domains and you only want to think about one at a time, the platform exposes [**Focus mode**](../features/focus-mode.md) (PRO, default off). Focus mode scopes the entire application — every list, dashboard, count, and search — to a single domain and its sub-tree, hiding everything else for the rest of your session.

It does not grant or revoke permissions; it just filters the view. Use it when:

- You operate across many client domains and want to work on one at a time.
- Your organisation is large enough that the "all domains" view is overwhelming for day-to-day work.
- You're running a demo or an onboarding and want the rest of the workspace out of the way.

When focus is engaged, all the cross-domain composition described above is suppressed — you'll only see assets, controls, and assessments from the focused sub-tree. Clearing the focus restores the full cross-domain view.

## Related

- [Domains](domains.md) — domain hierarchy, IAM groups, restructuring, moving objects.
- [Actors and teams](actors-and-teams.md) — who gets assigned what.
- [Understanding the IAM model](../configuration/organization/iam-model.md) — full configuration-side deep dive (SSO, MFA, PATs, accounting).
- [Focus mode](../features/focus-mode.md) — the PRO tool for scoping back the view.
- [User groups](../configuration/organization/user-groups.md) — how role assignments are actually stored and managed.
