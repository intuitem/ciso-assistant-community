---
description: Organisation-defined labels that override the platform's defaults
---

# Terminology

CISO Assistant ships with a default vocabulary for the values that appear in dropdowns and badges across the UI — risk origin types in EBIOS RM, project status values, qualifications on incidents, accreditation status labels, metric units, and so on. The **terminology** layer lets each organisation override those defaults to match its own internal vocabulary, without changing the platform's data model.

## Why it exists

Two organisations can use CISO Assistant against the same framework and the same methodology, but speak entirely different internal languages. One team's "Risk Origin: state-actor" is another team's "Adversary: nation-state". The terminology surface lets you reshape the labels without forking the platform.

## How it works

A terminology entry binds a **label** to a **field path** — the specific UI surface where the label appears. The shipped field paths today cover:

- `ro_to.risk_origin` — Risk Origin types on RO/TO couples in EBIOS RM.
- `qualifications` — qualification tags on incidents, risk scenarios, and BIA escalation thresholds.
- `accreditation.status` and `accreditation.category` — labels on accreditation records.
- `entity.relationship` — third-party relationship types.
- `metric_definition.unit` — units shown alongside metric values.
- `project.status` and `project.health` — workflow labels on projects.

For each field path, the platform ships a **built-in** set of entries (state, organised crime, terrorist, activist, … for risk origins, for example). You can:

- **Hide** built-in entries you don't want to surface — the `is_visible` flag controls dropdown inclusion.
- **Add** organisation-specific entries alongside the built-ins.
- **Translate** entries through the standard library translation mechanism.

The platform falls back to the built-in default whenever an entry is missing or hidden — terminology is additive on top of a working set, not a replacement.

## Scoping

Terminology entries live in the root folder by default, meaning they apply organisation-wide. Built-in entries cannot be deleted; they can only be hidden.

## Where you find it

In the sidebar under **Extra → Terminologies**. The feature is gated by the `terminologies` feature flag, which is on by default.

## Related

- [Vocabulary → Terminology](../introduction/vocabulary.md)
- [Custom roles](../configuration/organization/custom-roles.md) — a different kind of organisation-defined override
