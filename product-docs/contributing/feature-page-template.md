# Feature page template

> Copy this file to `features/<area>/<feature-slug>.md` (or `features/<feature-slug>.md` if there is no obvious area yet) and fill in the sections below. Delete this preamble in the copy.
>
> **Length guidance:** aim for one screen of skimmable content per section. If a section grows past a few paragraphs, consider splitting it into a sub-page and linking from here. The catalogue earns its keep by being scannable — long-form deep dives belong on the concept pages.

---

# {{ Feature name }}

_One or two sentences: what this feature is, and which problem it solves._

## For users

- **Where it lives.** Sidebar entry, URL, or workflow entry-point.
- **When to use it.** The trigger / pain it addresses.
- **How to use it.** The happy-path walkthrough — concise steps, screenshots if helpful.
- **What it gives you.** Outputs, exports, side-effects in the UI.

## For implementers

- **Surface area.** Backend models / Django app touched, frontend routes added, API endpoints exposed.
- **Key integration points.** What other features depend on this one. What it depends on.
- **Gotchas.** Anything surprising — permission rules, ordering, folder scoping, race conditions, library shape, migration concerns.
- **Configuration.** Feature flags, environment variables, library entries needed.

## Status

- **Shipped in:** commit / version / release tag
- **Owner:** team or person
- **Feature flag:** if applicable, name and default state
- **Edition:** community / enterprise / both

## Related

- Links to relevant concept pages, sibling features, or external standards.
