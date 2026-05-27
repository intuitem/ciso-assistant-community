---
description: Guidelines for designing reusable journey presets
---

# Journey preset authoring

> _Stub — to be expanded._

A **journey preset** is a reusable template for a journey — the bundle of audits, risk assessments, and supporting objects that a team applies to a new perimeter (e.g. _new project intake_, _supplier onboarding_, _annual ISO recertification_). Authoring a preset well turns repeated set-up work into a one-click instantiation, with consistent naming, owners, and scope across teams.

## Preset editor

The platform ships with an **in-app preset editor** — a visual designer that lets you assemble a preset step-by-step in the UI, without touching YAML. This is the **recommended authoring pattern going forward**.

You can reach it at **`/experimental/preset-editor`** in your instance. It's currently exposed under the _experimental_ namespace while the UX is being polished — the menu entry and URL are likely to move once it graduates, but the underlying tool is the same.

### What it does

- **Create blank** — _Create blank preset_ starts with an empty preset (optional name) and opens the per-preset editor where you'll add steps and the objects they scaffold.
- **Fork from library** — library-shipped presets are read-only by design; the _Fork from library_ panel lists them and creates a fully editable copy on _Fork_. This is the standard way to start from a known-good preset and tune it (rename, prune steps, change targets) instead of building from scratch.
- **Duplicate** — any user-authored preset can be duplicated as the starting point for a variant (e.g. a _Light_ and _Full_ flavour of the same onboarding journey).
- **Draft and publish lifecycle** — edits live in a draft on the preset until you publish; you can save, discard, or run a publish-preview before committing.

### What you can edit inline

The per-preset editor exposes the structural pieces of a preset:

- **Steps** — the ordered progression a team walks through when instantiating the preset. Add, insert at a position, reorder up/down, remove.
- **Scaffolded objects** — per step, the objects the preset creates at instantiation time: frameworks (audits), risk assessments, business impact analyses, EBIOS RM studies, and other journey-relevant types. Each scaffold carries its own defaults (name, library reference for framework-backed objects, owner placeholders).
- **Step targets** — what the step points at: nothing, a model the user picks at run time, a specific URL, or an object scaffolded by a previous step (cross-step references — e.g. _Step 3 risk assessment uses the perimeter created in Step 1_).
- **Parameters** — key-value defaults applied to scaffolded objects, so the same preset can produce sensibly-named outputs without manual editing after instantiation.
- **Metadata** — preset name, description, version, intended audience.

### When to use the editor

- **Editor** — for any preset that lives primarily on this instance, including in-progress drafts and forks of community presets. The editor is the right channel whenever you want immediate validation and re-use across teams on the same instance.
- **Library YAML** — for presets you intend to ship across instances or upstream to the community catalogue. YAML export and the library-publishing channel will be expanded in future revisions; until then, the editor remains the practical path and library presets are imported into the editor through _Fork from library_.

## What this page will cover

- **What belongs in a preset** — frameworks to spawn audits from, risk matrices to attach, default authors and reviewers, default folders.
- **Naming and parameterisation** — placeholders that get replaced at instantiation (perimeter name, year, owner), conventions to keep generated names readable.
- **Default ownership** — who should be pre-assigned at instantiation time vs. left blank to be filled in.
- **Scope expectations** — when a preset should default to a perimeter vs. a domain, and how that affects IAM.
- **Iteration** — updating a preset without disturbing existing journeys that were spawned from it.
- **Sharing** — how to make a preset reusable across domains (community edition) or sub-domains (PRO edition with [focus mode](../../features/focus-mode.md)).

## Existing material

- [Journeys concept](../../concepts/journeys.md) — what a journey _is_ in the data model.
- [Managing a project](../../guides/projects.md) — the closest existing walkthrough for a multi-assessment workflow.

## Related

- [Framework authoring](framework.md) — presets typically reference one or more frameworks you've authored.
- [Risk matrix authoring](matrix.md) — presets typically reference a default matrix.
- [Initial setup](../../guides/initial-setup.md) — the first journey for a fresh instance.
