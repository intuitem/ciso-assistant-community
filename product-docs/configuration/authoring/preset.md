---
description: A complete guide to authoring journey presets — designing the step sequence, scaffolding objects, cross-step focus, and the draft/publish lifecycle
---

# Journey preset authoring

A **journey preset** is a reusable template for a journey — the bundle of audits, risk assessments, and supporting objects that a team applies to a new perimeter (e.g. _new project intake_, _supplier onboarding_, _annual ISO recertification_). Authoring a preset well turns repeated set-up work into a one-click instantiation, with consistent naming, owners, and scope across teams. This page is a complete walkthrough of the **in-app preset editor**.

## Preset editor

The platform ships with an **in-app preset editor** — a visual designer that lets you assemble a preset step-by-step in the UI, without touching YAML. This is the **recommended authoring pattern going forward**.

You can reach it at **`/experimental/preset-editor`** in your instance. It's currently exposed under the _experimental_ namespace while the UX is being polished — the menu entry and URL are likely to move once it graduates, but the underlying tool is the same.

### Opening the editor

The landing page is the **preset hub**, organised as three sections:

#### Start something new

Two entry points side by side:

- **Create blank preset** — names a fresh preset _Untitled preset_ (or any name you typed in the optional field) and opens its editor immediately. Use this when you're designing a journey from scratch.
- **Fork from library** — expands a panel listing every library-shipped preset on the instance (name, version, URN, description). Picking _Fork_ on a library preset creates a fresh editable copy of it and opens the editor on the clone.

Library-backed presets are read-only by design — they ship from YAML libraries and stay upgradable. Forking is the only path to edit one; the original library preset stays intact, and the fork is independent (later library upgrades won't touch your fork).

#### Your presets

A table of every user-authored preset on the instance, ordered by most recently updated. Columns: _Name / Version / Updated / Actions_. Actions are:

- **Open** — go to the per-preset editor.
- **Duplicate** — create an editable copy (the same forking primitive used on library presets, applied here to your own work). Useful for spawning variants of an existing preset (_Light_ / _Full_ flavours).
- **Delete** — removes the preset entirely. Confirmation required.

#### Library presets (under _Fork from library_)

A grid of library-backed presets, each showing name, version, and URN. They're not directly editable; **Fork** is the action.

### The per-preset editor

Opening a preset jumps to `/experimental/preset-editor/{id}`. The layout:

- A **sticky toolbar** at the top with status pill and lifecycle actions.
- An **inline metadata block** for preset name + description.
- A **Steps section** below — the heart of the editor.

#### The toolbar at a glance

- **Back arrow** to the preset hub.
- **Status pill** describing the draft state:
  - **Unsaved changes** (amber) — the in-memory edit differs from the server-side draft. Save to persist.
  - **Published v{n}** (green) — the draft matches the last published version.
  - **Draft** (grey) — the preset has a draft but has never been published.
  - **Published!** (green, transient) — flashes for ~3 seconds after a successful publish.
- **Save** — visible only when dirty. Persists the in-memory state to `editing_draft` on the server.
- **Discard** — with inline confirmation. Throws away the server-side draft and reloads from the last published state (or a fresh blank if this preset has never been published).
- **Publish** — triggers a publish preview (see below). Disabled while there are unsaved changes; save first.

A **`beforeunload`** guard prompts before the browser tab is closed or refreshed with unsaved changes, and SvelteKit's `beforeNavigate` does the same for in-app navigation. Library-backed presets opened directly (not forked) show a read-only banner instead of the editor, with a link back to the fork action.

#### Preset metadata

Two inline-editable fields at the top of the body:

- **Preset name** — the human-readable label, e.g. _Annual ISO 27001 audit_, _Vendor onboarding_.
- **Description** — what this preset is for, who runs it, when. Optional but recommended — this is what teammates see when picking a preset.

### Steps

A preset is a **sequence of steps**, each of which represents one milestone or one screen in the instantiation flow. The pattern is: _at this step in the journey, the user is here, and the platform creates/links these objects_.

The editor renders every step as a card with a coloured left border (cycling blue / violet / amber / emerald by position) so the sequence is visible at a glance. Between every pair of cards (and above the first, below the last), a hover-only **_Insert step_** separator lets you splice a new step in at any point.

#### Step controls

Per step:

- **Reorder** — _Move up_ and _Move down_ buttons swap with the adjacent step.
- **Delete step** — confirmation prompt. If the step owns any scaffolded objects, the prompt lists them and warns that they'll be removed too. Any other step that focused on a deleted scaffold has its focus cleared.

#### Step fields

- **Key** — the step's stable identifier within the preset (auto-generated as `step_1`, `step_2`, etc., but editable). Used internally to link scaffolds to steps and to allow another step to focus on this step's outputs.
- **Title** — the human-readable label shown to the user at instantiation time (_"Set up the perimeter"_, _"Run the audit"_).
- **Description** — optional, additional context shown beneath the title.

### Step targets — pointer mode

Each step can _point at_ something — what the user lands on when they advance to this step. Three pointer modes, picked via a tab-style toggle:

- **None** — the step has no target. The user sees the title and description, and advances.
- **Model** — the step points at a model (a route in the app, like `compliance-assessments`, `applied-controls`, `assets`). Combined with a `target_ref`, it can land the user on a specific scaffolded object.
- **URL** — the step points at an arbitrary URL (internal or external). Useful for embedded handbook links, external SOPs, or third-party tools.

#### Model mode — target_model and target_ref

When pointer mode is **model**, two dropdowns appear:

- **Target model** — every scaffoldable type plus a curated list of nav-only models (see [What can be scaffolded](#what-can-be-scaffolded) below). Examples: `compliance-assessments`, `risk-assessments`, `applied-controls`, `assets`.
- **Target ref** — once a model is picked, this dropdown lists every scaffolded object in the preset whose type matches the model. The user can pick:
  - An object owned by **this** step (the default — the step scaffolds it and immediately focuses on it).
  - An object owned by **another step** (cross-step focus — multiple steps can point at the same scaffold, which is how a preset can have three steps that all act on the same audit).
  - Nothing — the step lands on the model's list page rather than a specific object.

The picker labels objects with their `ref` so you can tell which is which when several scaffolds of the same type exist.

#### URL mode — target_url

When pointer mode is **url**, a single text input takes the URL. No validation — anything that parses as a URL works, including relative paths.

#### Switching pointer mode

Switching mode preserves the data for the mode you came from where reasonable:

- **None → Model** — empties `target_url`, asks you to pick a model.
- **Model → URL** — empties `target_model` and `target_ref`; asks you to type the URL.
- **Model → Model with different type** — clears `target_ref` if it pointed at a scaffold whose type doesn't match the new model. Step-owned scaffolds whose type doesn't match the new model get converted (preserving name / description / ref, resetting type-specific fields).
- Anything → **None** — clears all target fields.

### Scaffolded objects

A scaffold is a description of an object the preset will _create_ at instantiation time. Each scaffold lives in the preset's `scaffolded_objects` array and carries:

- **`ref`** — a stable identifier within the preset (must be unique). Used to wire cross-step focus.
- **`type`** — the object kind (`compliance_assessment`, `risk_assessment`, etc.).
- **`name`** and **`description`** — defaults for the object when it gets created.
- **`step_ref_id`** — the key of the step that "owns" this scaffold. Owned scaffolds render inline inside that step's card.
- Type-specific fields (framework URN, risk matrix URN, category, asset type — see below).

#### Adding a scaffold

Inside any step whose target model is set, click **Add object** to scaffold a new object of the appropriate type:

- A unique `ref` is auto-generated from `{step_key}_{type}` (with a numeric suffix if needed).
- The type comes from the step's target model.
- The scaffold defaults to a sensible empty state for that type (e.g. `framework: ''` for compliance assessments).
- If the step has no `target_ref` yet, the first added scaffold becomes the step's focus automatically — a one-click "create and open" pattern.

#### What can be scaffolded

The editor knows how to scaffold every primary journey object:

| Type | Target model | Extra fields |
|---|---|---|
| `compliance_assessment` | `compliance-assessments` | Framework (library URN), Implementation groups |
| `risk_assessment` | `risk-assessments` | Risk matrix (library URN) |
| `business_impact_analysis` | `business-impact-analysis` | Risk matrix (library URN) |
| `ebios_rm_study` | `ebios-rm` | Risk matrix (library URN) |
| `findings_assessment` | `findings-assessments` | Category (pentest / audit / review / other) |
| `processing` | `processings` | — |
| `entity` | `entities` | — |
| `task_template` | `task-templates` | — |
| `organisation_objective` | `organisation-objectives` | — |
| `organisation_issue` | `organisation-issues` | — |
| `perimeter` | `perimeters` | — |
| `asset` | `assets` | Asset type (SP / PR) |

#### What can be targeted but not scaffolded

A second category of models can be the step's target but the preset doesn't create them — the user is just landed on their list page:

- `accreditations`
- `actors`
- `applied-controls`
- `evidences`
- `incidents`
- `metric-instances`
- `policies`
- `risk-acceptances`
- `security-exceptions`

These types exist in the platform as standalone records and don't need a preset to spawn them; the preset just routes the user to the relevant list.

#### Type-specific scaffold fields

##### Compliance assessment

- **Framework** — a dropdown of every loaded framework library. The selection stores the **library URN**, not the framework's own URN (because the executor resolves library URNs at instantiation time, which keeps the preset portable across instances where the same library has different framework IDs).
- **Implementation groups** — once a framework is picked, this chip list shows every IG defined on that framework. Tick the IGs the spawned audit should scope to. Empty selection means _all requirements_.

##### Risk assessment / BIA / EBIOS RM study

- **Risk matrix** — a dropdown of every loaded risk matrix library. Like frameworks, the stored value is the **library URN**.

##### Findings assessment

- **Category** — one of `pentest`, `audit`, `review`, `other`. Drives the spawned findings assessment's default category.

##### Asset

- **Asset type** — `SP` (Support asset) or `PR` (Primary asset).

#### Parameters

Every scaffold can carry a **parameters** key-value dict (`target_params`) used to seed additional fields on the spawned object. The editor exposes this as a rows-of-key-value-pairs UI: arrays are written as comma-separated values, plain strings stay as-is. Parameters are the escape hatch when a scaffold needs a field the editor doesn't otherwise expose (e.g. a default `description` template, an opinionated `owner`).

#### Cross-step references

A single scaffold can be focused on by multiple steps:

- Step 1 (target: `perimeters`) scaffolds `perimeter_1` — the perimeter the journey is about.
- Step 2 (target: `compliance-assessments`) scaffolds `iso_audit` — the ISO audit on that perimeter.
- Step 3 (target: `compliance-assessments`) **focuses on `iso_audit`** via the cross-step picker, without scaffolding a second audit. Use case: split the audit work into _Setup_ and _Run_ steps that both land on the same audit page.
- Step 4 (target: `risk-assessments`) scaffolds `risk_study` — a risk assessment also tied to `perimeter_1`.

The cross-step focus dropdown lists every scaffold matching the step's target model, including ones owned by other steps. Renaming a scaffold's `ref` automatically updates every step that pointed at it, so refactors stay consistent.

### The draft → publish lifecycle

The preset editor uses a server-side **editing draft** that's distinct from the live preset:

1. **Start editing** — the first time you open the editor for a user-authored preset, the server creates an `editing_draft` JSON from the current live state. Re-opening returns the same draft (idempotent).
2. **Save draft** — `Save` PATCHes the in-memory state onto the server. The status pill becomes _Published v{n}_ when the draft matches live, or _Draft_ if nothing has been published.
3. **Publish preview** — clicking **Publish** runs a preview: the server returns the list of step keys that would be **deleted** from the live preset by publishing. If the list is empty, publishing happens immediately. If it's not, a modal lists the deletions for review.
4. **Publish** — commits the draft. The server reconciles the draft into the live preset, bumping `editing_version`.
5. **Discard draft** — deletes the server-side draft and reloads from the last published state.

Step deletions in the publish preview matter because removing a step from a preset that's already been instantiated can leave instances in a broken state — the modal exists to give you a clear "this is what you're about to lose" warning before commit.

### What the editor doesn't do (yet)

A few gaps to be aware of:

- **YAML export** — presets currently flow library-in (via `Fork from library`) but not editor-out as a library file. A preset authored in the editor stays on this instance until that export channel ships.
- **Translation editing** — presets carry a `translations` block on each step, but the editor doesn't yet expose it as side-by-side editing the way the framework and matrix builders do. Translations need YAML editing for now.
- **Bulk step operations** — no multi-select, no copy/paste of steps across presets. You can _Duplicate_ a whole preset and prune; that's the workaround.
- **Validation** — beyond required-fields checks, the editor doesn't validate cross-step focus consistency at edit time. The publish preview is the validation surface.

For these, fall back to library YAML editing as described in [Designing your own libraries](../libraries/custom-libraries.md).

## Editorial discipline

The editor gives you a lot of flexibility; the presets that actually save teams time are narrower. A few principles:

### Keep steps thin

- **One milestone per step.** A step that lands on three different objects ("set up the perimeter, then the audit, then the risk assessment") is three steps, not one. The instantiation UI uses the step boundaries as natural pause points; collapsing them defeats the purpose.
- **Title each step like a verb phrase.** _"Define the perimeter"_, _"Run the audit"_, _"Document risks"_. The title is what users see in the journey progress; it should describe what they're doing, not what the step contains.

### Scaffold what's reusable, point at what's existing

- **Scaffold objects the preset always creates** — the audit, the perimeter, the risk assessment. These are why the preset exists.
- **Don't scaffold objects the user picks at run time** — a step that lands the user on `assets` (the list, no `target_ref`) is the right model when the user is supposed to pick or create their own asset, not when the preset has one in mind.
- **Cross-step focus is the right tool for shared objects.** When several steps act on the same audit, scaffold it once, focus on it from each step. Scaffolding the audit twice creates two audits at instantiation time.

### Names and refs

- **Scaffold `ref`s are internal identifiers.** Keep them short and stable (`iso_audit`, `vendor_perimeter`). The user never sees them; what they see is the scaffold's `name` field.
- **Scaffold `name`s become the spawned objects' names.** Use placeholders sparingly — the spawned object can always be renamed at instantiation.

### Library URNs vs object IDs

The framework and risk-matrix scaffold fields store the **library URN**, not the framework's or matrix's own URN. This matters because:

- A preset shipped as a YAML library can be loaded on any instance and resolves correctly as long as the referenced framework library is also loaded.
- If you _Save as YAML_ a preset that references a framework's own URN, that URN may not exist on another instance — but the library URN will, because libraries are designed to be portable.

The editor handles this automatically — you pick from a "loaded library" dropdown, not a "loaded framework" dropdown. The published preset stores the right thing.

### Sharing presets across teams

- **Domain-scoped sharing** — a preset created on one instance is available to every user who has access to it through IAM. Use the preset's folder ownership to control visibility.
- **Forking instead of editing** — when a team wants their own variant of a shared preset, _Duplicate_ produces an independent fork. Edits on the fork don't propagate back to the source, which is usually what's wanted.

## Existing material

- [Journeys concept](../../concepts/journeys.md) — what a journey _is_ in the data model.
- [Managing a project](../../guides/projects.md) — the closest existing walkthrough for a multi-assessment workflow.

## Related

- [Framework authoring](framework.md) — presets typically reference one or more frameworks you've authored.
- [Risk matrix authoring](matrix.md) — presets typically reference a default matrix.
- [Initial setup](../../guides/initial-setup.md) — the first journey for a fresh instance.
- [Excel-driven authoring](excel.md) — the wider library-YAML workflow.
