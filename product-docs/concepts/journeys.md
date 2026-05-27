---
description: Guided, step-by-step workflows that bootstrap a domain along a recognised path
---

# Journeys

A **journey** is a guided, step-by-step workflow that walks a domain through a recognised process — getting an organisation ready for ISO 27001 certification, running a DORA readiness assessment, building out a privacy register, and so on.

Journeys remove the "what do I do first?" problem. Instead of staring at an empty domain and assembling the right libraries, assessments, and tasks by hand, you pick a journey, apply it to a domain, and start working through the prescribed steps.

## Preset vs journey

Journeys come in two flavours of object that mirror the **Framework → Audit** pattern elsewhere in the platform:

- A **preset** is the template. It bundles a set of starter objects (typically an audit, a risk assessment, sometimes additional scaffolds) plus an ordered list of steps with descriptions and links into the platform. Presets are versioned and shipped via libraries; they can also be authored locally.
- A **journey** is an instance of a preset, materialised in a specific domain. Applying a preset creates the scaffolded objects in the chosen domain and copies the step list onto the journey so that step statuses can be tracked independently from any other journey.

The same preset can be applied to multiple domains and yields a distinct journey each time.

## Lifecycle

1. **Browse the catalogue.** The presets page lists everything available on the instance — library-backed presets shipped with CISO Assistant (ISO 27001 starter, DORA readiness, NIS2, sector-specific bundles, etc.) and any presets authored locally. Filter by region tag to narrow the list.
2. **Apply to a domain.** Pick a target domain (or create one on the fly). Optionally let the journey **create the scaffolded objects** for you and apply any **feature flags** the preset suggests.
3. **Work the steps.** Each step has a title, description, and either a target object (e.g. "open the SOA review for the ISO audit") or a target URL inside the platform. Mark steps as **in progress**, **done**, or **skipped** as you advance, and add notes.
4. **Track progress.** The recently-active journeys panel shows a progress ring per journey; the underlying step counts feed dashboards.
5. **Upgrade when a newer preset ships.** When a library-backed preset is updated, journeys derived from it flag an upgrade. Upgrading re-applies the newer template while preserving user-state (statuses and notes) on steps that survived the new version.

## What's inside a preset

- **Scaffolded objects** — the assessments and supporting records that get created when the preset is applied. Typical scaffolds include compliance assessments (with framework + implementation-group selection), risk assessments (with a chosen matrix), and occasionally task templates, perimeters, or entities.
- **Steps** — an ordered list of actions to perform. Each step can point at a scaffolded object (via a named reference resolved at apply time) or at a generic internal route such as the SOA results page. Steps carry translations so the workflow speaks the user's language.
- **Feature flags** — some presets enable optional features when applied (reports, sec-intel feeds, etc.), letting the journey come with a fully-configured environment.
- **Dependencies** — required libraries (frameworks, matrices) that must be loaded for the preset to apply cleanly.

## Permissions

Applying a preset requires permission to load libraries on the target domain. Viewing journeys and updating their step statuses follows the standard domain-scoped permission model — see [Understanding the IAM model](../configuration/organization/iam-model.md).

## Related

- [Vocabulary → Preset](../introduction/vocabulary.md)
- [Libraries](libraries.md)
- [Audits](audits.md)
- [Risk assessments](risk-assessments.md)
