---
description: Author a whole library — frameworks, matrices, threats, controls, presets — as a draft document, then publish it through the standard loader
---

# Library builder

The **Library builder** is the single place to author library content in CISO Assistant. It lives at **`/experimental/library-builder`** and replaces the earlier per-object builders (framework builder, matrix editor, preset editor): they are now surfaces _inside_ one builder rather than separate tools.

You edit a **draft document** — a `LibraryDraft` — not live database objects. Think of it as a spreadsheet editor for a library: you assemble frameworks (with requirement trees that can reference reference controls and threats), risk matrices, threats, reference controls, and journey presets into one draft, and nothing touches the live catalog until you **publish**. Publishing hands the draft to the **standard library loader** — the same code path that imports any built-in or community library — so authored content behaves exactly like everything else: versioned, upgradable, exportable.

Because a draft serializes to a plain library **YAML**, you can also export it and re-import it on another instance, or import an existing library YAML straight into a new editable draft.

{% hint style="warning" %}
**Experimental.** The library builder is exposed under the `/experimental/` namespace while its UX is being polished. The URL and menu entry may move once it graduates, and individual surfaces may change between releases. Your drafts and published libraries are not at risk. Feedback is welcome.
{% endhint %}

## Concepts in one minute

- **Draft (`LibraryDraft`)** — the working document. Editing a draft never mutates live objects.
- **Identity** — a library is identified by its **packager** and **ref_id** (e.g. `packager = acme`, `ref_id = my-policy`). Every URN in the library derives from them: `urn:acme:risk:framework:my-policy`. Identity is **editable while the library is a draft** and **frozen on first publish** — renaming a draft rewrites the whole URN family for you; once published, it's locked.
- **Publish** — the library-level action (on the draft page) that hands the draft to the standard loader, materializing its objects live and freezing the identity.
- **Library publication states** (the badge on the draft page and the builder list):
  - **Draft** — never published; identity still editable.
  - **Published** — published, with no changes since.
  - **Published · unpublished changes** — published, but edited since; publish again to push the edits live.
- **Save state** — separate from publication. Inside each object editor (framework/matrix/preset) the badge tracks whether your local edits are **saved to the draft** yet — **Empty**, **Saved to draft**, or **Unsaved changes**. You save in the editor; you publish from the draft page.
- **Adopt** — bring an existing custom library (or a library-less framework left by the old builders) into a draft so you can keep editing it, identity preserved.
- **Clone** — copy objects _by value_ from another library or draft into yours, rebased onto your URN family so they evolve independently.

## Getting started

### Author a single framework or matrix (simple mode)

For the common case — one framework, or one matrix, with no other objects — you don't need to think about libraries at all.

1. Go to **`/experimental/library-builder`**.
2. Click **New framework** or **New matrix**.
3. Enter a **name** and a **packager** (your namespace, e.g. `acme`). The packager is remembered after the first time, and the default can be set instance-wide (see [Set the default packager](#set-the-default-packager)).
4. Click **Create and edit**. The wrapping library is minted behind the scenes — its ref_id is slugged from the name and de-duplicated against your corpus — and you land straight in the object's editor.
5. Edit and save, then publish from the draft page.

The draft page shows a **Simple view** for single-object libraries and a toggle to the **Full view** when you need the library-level surfaces.

### Author a full library (multiple objects)

1. Go to **`/experimental/library-builder`** and click **New Library Draft**.
2. Set the **name**, **packager**, and **Reference ID** (the ref_id). The assembled URN previews live below the inputs, and an identity check warns if it collides with an existing library or object ("This identity collides with … existing object(s)") or confirms "Identity is free."
3. Click **Create**. You land on the draft page in Full view.
4. Add objects from the draft page:
   - **Framework** — opens the framework editor (requirement tree, scoring, implementation groups, and node-level references to reference controls and threats).
   - **Risk matrix** — opens the matrix editor (levels, grid, palette, translations).
   - **Threats** and **Reference controls** — table editors for the catalog objects a framework can reference.
   - **Preset** — a journey preset that scaffolds objects for a recurring assessment.
5. Save as you go. The draft's **Contents** column summarizes what it holds (e.g. _1 framework, 2 threats_).
6. Publish when ready (see [Publishing and lifecycle](#publishing-and-lifecycle)).

## Authoring frameworks

A framework is a tree of **requirement nodes**. Open the framework editor from a draft, then use these recipes. You don't have to start from a blank page — [adopting or cloning](#bringing-in-existing-content) an existing framework is often the faster route.

### Build the requirement tree

1. Click **Add top-level node** at the bottom, or the **Add child** menu inside an existing node to nest.
2. Pick a preset from the node-type menu:
   - **Blank node** — start empty and flip the flags yourself.
   - **Group** — a section header (not assessed).
   - **Requirement** — a leaf the analyst will answer.
   - **Splash screen** — a presentational markdown block (intro, methodology).
3. Fill in the **ref_id** (e.g. `5.3.2`) and **name**. The name field warns past 180 characters (200-character limit).
4. Grow the tree from the keyboard:
   - `Alt + →` / `Alt + ←` — indent / outdent the focused node.
   - `Alt + Enter` — add a child; `Alt + Shift + Enter` — add a sibling below.
   - `⌘ + .` / `Ctrl + .` — toggle assessable.
5. Drag the grip handle (left of any node) to reorder against siblings.
6. Save with `⌘ + S` / `Ctrl + S` as you go — the editor's badge flips between **Unsaved changes** and **Saved to draft**.

### Add implementation groups (IGs)

For tiered selection (e.g. _Basic_ / _Standard_ / _Advanced_):

1. Open **Framework Settings** → **Implementation groups** → **Add group**, and set each group's **ref_id** (`IG1`), **name**, **description**, and **Selected by default**.
2. On each requirement node, use the **Implementation groups** chip selector to tick the IGs that include it. An empty selection means _every IG_ includes the node.

See [Implementation groups](../../concepts/audits.md#implementation-groups) for the conceptual context.

### Add a scoring scale

1. Open **Framework Settings** → the scoring section.
2. Set **Minimum score** and **Maximum score** (e.g. 0–5 for CMMI-style, 0–100 for percentage).
3. Choose **Aggregation**: _Average_ (leaf scores average up to the parent) or _Sum_.
4. Under **Score scale**, **Add scale level** for each level and set its **score**, **name** (_Initial_, _Managed_, _Defined_…), and **description** (the criteria for reaching it).

Match the standard the framework comes from (CMMI 0–5, NIST CSF 2.0 1–4) rather than inventing a scale, and document each level so an analyst can tell level 3 from level 4. (Per-requirement score overrides are a library-YAML feature, not exposed in the builder UI — author them in [Excel/YAML](excel.md) if you need them.)

### Add questions and choices

On a requirement node, click **Add question**:

- **Boolean** — a yes/no question (e.g. _"Is the policy reviewed annually?"_). Use the Advanced disclosure to set a **weight** or a **depends_on** rule (show only when a previous question on the node has specific answers).
- **Single choice** — a scoring question where each choice contributes points. Under the question, **Add choice** and set per choice:
  - **Value** — the label.
  - **Score** (`add_score`) — points contributed when picked.
  - **Result** (`compute_result`) — optionally map to a compliance result (`compliant`, `partially_compliant`, `non_compliant`, `not_applicable`). Contributing choices aggregate _worst-wins_, with `not_applicable` neutral. The legacy literals `true` / `false` are still read as `compliant` / `non_compliant`.
  - **Color** — optional, for visual differentiation.

The order in the editor is the order respondents see. Keep conditional (`depends_on`) chains shallow — a single hop is easy to reason about; chains are expensive to debug.

### Add outcome rules

To label a result based on the final score (_Bronze_ at 60+, _Silver_ at 80+, _Gold_ at 95+):

1. Open **Framework Settings** → **Outcome rules** → **Add rule**.
2. Per tier, set a **ref_id** (`bronze`), a **CEL Expression** (a boolean, e.g. `score >= 60`), a **Label** (what reaching this tier means), and a **color**.
3. All matching rules apply, so order doesn't matter; use the literal `true` as a catch-all default tier. The **CEL context reference** toggle lists the context variables available in expressions (`assessment.*`, `requirements[...]`, `answers[...]`).

### Reference reference controls and threats from a requirement

A requirement node has **Add reference control** and **Add threat** pickers. Each offers the objects available to the draft — those defined in the same draft, plus objects from libraries the draft **depends on** — with tabs to _link an existing_ object, _create a new_ one, or browse another library. Picking an object from another library automatically records the dependency so the reference resolves at load time.

Bundle controls and threats in the same library as the framework when the framework prescribes its own catalogue (e.g. CIS Controls v8); otherwise ship them separately so the framework stays leaner and users can mix and match.

## Authoring risk matrices

A risk matrix declares the **probability** scale, the **impact** scale, and the **risk** levels their combination yields. New matrices seed as 3×3. The matrix editor page presents its content as stacked sections — **Probability**, **Impact**, **Risk**, and **Grid** — and its only action is **Save to draft**; validation and publishing happen at the library level from the draft page.

### Set up the levels

1. Fill in the matrix **name** and optional description.
2. In the **Probability** section, use **Add level** / **Remove level** (the trash icon) to reach the count you want (a 5×5 needs 5). Per level set the **abbreviation** (`VL`, `L`, `M`, `H`, `VH`), **name**, **description** (anchor it with numbers where you can — _"More than 10 per year"_ is testable, _"Frequent"_ isn't), and a **Color**.
3. Repeat in the **Impact** section.
4. In the **Risk** section, set the number of risk classes and each one's name, description, and colour.

The editor enforces a minimum of 2 levels per axis.

### Edit the grid

The **Grid** section maps every `(probability, impact)` pair to a risk level:

- **Click** a cell to cycle to the next risk level, or **hover** it and pick a level directly from the dropdown. Focusing a cell and pressing `Enter` / `Space` cycles too.

Deleting a risk level that cells still point at is the most fragile operation: affected cells fall back to the first risk level. Prefer cloning to a new matrix over destructive level removal on a matrix already in use. (The publishable check surfaces such issues when you **Validate** on the draft page — see below.)

### Apply a colour palette

Each level section offers four colour palettes — **classic** (green→red), **accessible** (Wong's colourblind-safe set), **warm**, and **cool** — as swatch buttons. Selecting one rewrites every colour in that section in order (overwriting custom hex). Apply the same palette across sections for a coherent look; the _accessible_ palette is the safe default, and keeps risk-level colours monotonic (green → yellow → orange → red).

## Authoring journey presets

A **journey preset** is a reusable template for a journey — the bundle of audits, risk assessments, and supporting objects a team applies to a new perimeter (_new project intake_, _supplier onboarding_, _annual ISO recertification_). Open the preset editor from a draft.

### Add steps

1. Click **Add step**, or hover the gap between two steps and click **Insert step** to splice one in.
2. Per step set a **title** (a verb phrase users see in the journey progress — _"Define the perimeter"_, _"Run the audit"_), an optional **description**, and an **ID** (auto-generated `step_1`…; edit to something meaningful like `perimeter_setup`).

Keep one milestone per step — the instantiation UI uses step boundaries as natural pause points.

### Point a step at something

Each step can land the user on _something_ when they reach it. Set the pointer mode:

- **None** — no landing target.
- **Model** — a model list page (e.g. `assets`, `applied-controls`) where the user picks or creates their own, _or_ an object the preset scaffolds (see below).
- **URL / report** — an external SOP or embedded handbook link (relative or absolute).

### Scaffold objects

When a step should create an object at instantiation time, set its target model and click **Add {type}** (e.g. _Add compliance assessment_). Supported target models:

- **`compliance-assessments`** (audit) — set **ref**, **name**, a **framework** (from the loaded-library dropdown), and the **implementation groups** to scope to.
- **`risk-assessments`** / **`business-impact-analysis`** / **`ebios-rm`** — set ref, name, description, and a **risk matrix** where applicable.
- **`findings-assessments`** — set ref, name, and a **category** (`pentest`, `audit`, `review`, `other`).
- **`assets`** — set ref, name, and an **asset type** (`SP` Supporting / `PR` Primary).

The step focuses on the scaffold you just added. Scaffold objects the preset always creates; point (no scaffold) at objects the user supplies.

The framework and matrix fields store the **library URN**, not the object's own URN — so a preset shipped as YAML resolves on any instance where the referenced library is loaded. The editor handles this: you pick from a loaded-library dropdown.

### Cross-step focus and parameters

- **Cross-step focus** — to have several steps act on the _same_ scaffold (_"Set up"_ → _"Fill in"_ → _"Sign off"_ on one audit): scaffold the object once on one step, then on the others (same target model) use the **Or open a scaffold from another step** dropdown to point at it. Renaming the scaffold's ref updates every step that points at it. Scaffolding twice creates two objects.
- **Parameters** — a step whose pointer mode is **URL / report** has a **Params** section with **Add param** for key/value parameters (comma-separate a value for arrays).

## Multi-language authoring

Frameworks, matrices, and presets all support translations, with the same flow:

1. In the object's settings (or the Languages strip), add a **target language** from the dropdown.
2. Switch to that language with the **language selector** — the editor enters translation mode, splitting every translatable field into a read-only base value and an editable translation.
3. Click **Copy base** to seed untranslated fields with the base content as a starting point (existing translations are preserved), then walk through every field. An asterisk (`*`) flags fields that still have no translation, and a `translated/total` counter shows live coverage — it turns green at 100%.
4. Save.

Author in the base language first, and don't translate `ref_id`s, URNs, or matrix abbreviations — they're identifiers, not user-facing text. Removing a language (via the `×` on its chip) drops every translation for it, after a confirmation.

## Bringing in existing content

### Import a library YAML

1. On the builder list, click **Import YAML** and choose a `.yaml` / `.yml` file.
2. The file is parsed and validated, and a **new editable draft** is created from it.
3. The **packager and Reference ID remain editable** (the draft is not published), so you can rename the identity — renaming rebases the whole URN family — before publishing under your own namespace.

### Adopt a custom library

To keep editing a library that's already loaded:

1. On the builder list, pick the library from the **Adopt a custom library…** select and click **Adopt**.
2. A draft is created that keeps the library's identity. Editing and re-publishing upgrades the loaded objects in place.

Library-less frameworks left by the retired standalone builder appear in the same select under **Custom frameworks (no library yet)** and can be adopted the same way.

Adopt applies only to **custom** libraries (`builtin = false`) — you can't adopt a library shipped with the product, because its identity isn't yours. Built-in content can still be **cloned** or **referenced**.

### Clone objects from another library or draft

When building a draft, copy objects **by value** from an existing source:

1. In the draft's **Import objects (clone)** card, use the source select. It groups **Stored libraries** and **Your drafts**.
2. Pick the source and the objects to copy. They are copied into the current draft and **rebased** onto its URN family, so the clones belong to your library and evolve independently of the source.

When a cloned framework references a control or threat _outside_ the selection, you choose per reference how to resolve it: **skip** (drop the link — a self-contained framework, the default), **pull-in** (also copy the referenced object), or **reference** (keep the original URN and record a dependency on the source library).

## Publishing and lifecycle

Publishing is a **library-level** action on the draft page. The object editors (framework/matrix/preset) only **save to the draft**; you publish the whole library from the draft page toolbar, which has three controls: **Validate**, **Export**, and **Publish**.

### Validate

Click **Validate** to run the publishable check. The result renders in a panel: it reports **This library is publishable** when clean, or lists **errors** (which block publishing) and **warnings**. Use it before publishing to catch problems — unresolved references, a matrix with out-of-range cells, a name over 200 characters, and so on.

### Publish

Click **Publish** to hand the draft to the loader. On the first publish this **freezes the library's identity** (its URN family) and materializes the live objects. Re-publishing updates the existing library in place, by URN, so dependents (audits, mappings, other libraries) follow the same object identities.

The server enforces the rules and the UI prompts you when needed:

- **Version bump** — re-publishing changed content requires a higher version; you're asked to confirm the bump. Content that hasn't actually changed is refused.
- **Score-boundary changes** — if a scoring change affects existing assessments, a panel asks you to choose a **strategy** before the publish proceeds.
- **Removing preset steps** — if publishing would drop steps from a preset already in use, you're warned (with a count of steps that have user progress) and asked to continue.
- **Validation errors** — a failing publish drops the error list into the validation panel.

Only the objects and audits you're allowed to see are considered — the whole flow is RBAC-scoped.

The publication badge on the draft page (and the builder list) reflects the result: **Draft**, **Published**, or **Published · unpublished changes**, with the last-published timestamp shown alongside.

### Export as YAML

Click **Export** to download the library in library-format YAML — ready to load on another instance via the [Libraries](../libraries/README.md) section, or to commit to source control. If the draft has unpublished changes, export asks you to **publish first** (or confirm you want a working-copy export of the unpublished draft). In the framework editor, the **Export** control shows a warning indicator while you have _unsaved_ local edits — save first so the export reflects the saved draft.

### Revert edits (preset editor)

The preset editor has a **Revert** control that throws away edits since the last save and reloads the last saved draft. The framework and matrix editors and the draft page don't have a revert/discard control — to abandon an object entirely, delete it from the draft.

## Delete an object from a draft

Each framework, matrix, and preset card in the Full view has a **delete** button. Deleting removes the object from the draft document only — it doesn't touch anything live. If the object is still referenced elsewhere in the draft (e.g. a control or threat linked from requirement nodes), you're warned and asked to confirm; confirming removes the links and deletes the object. Deleting a step from a preset already instantiated in a journey can leave that journey broken — the publish flow warns about step removals so you can review before committing.

## Editorial discipline

The builder will let you do almost anything; the choices that age well are narrower.

**Frameworks**

- **Prefer breadth over depth.** Two levels suit most standards; three is the realistic limit before navigation hurts. If a section has a single assessable child, flatten it.
- **Stable `ref_id`s outlive renames.** They appear in mappings, exports, and analyst conversations ("we're failing 5.3.2"). Zero-pad so they sort (`05.03.02`, not `5.3.2` past 9).
- **The URN namespace identifies the publisher, not the framework** — one namespace per organisation (`acme`), with the ref_id differentiating frameworks. Settle it before publishing widely; once published the identity locks.
- **Add IGs only when there are two real tiers**, and prefer cumulative tiers (IG1 ⊂ IG2 ⊂ IG3). **Match the standard's scoring scale** rather than inventing one, and document each level.
- **Drive flash-mode scoring from choice `add_score`**, not manual per-requirement scoring — the question layer is the structured-input layer.

**Risk matrices**

- **Pick the size deliberately.** 3×3 for early programmes, 5×5 for mature ones (ISO 27005, EBIOS RM, NIST). Beyond 5×5, discrimination doesn't actually improve.
- **Anchor axis levels with numbers**, keep one term (likelihood / frequency / probability), and mirror the business's own impact grading.
- **Keep risk-level colours monotonic** and lean on the _accessible_ palette. Make the acceptable-vs-unacceptable boundary visually obvious.
- **Once in use, changes ripple.** Renaming/recolouring/adding levels is safe; removing a level or changing a cell re-evaluates scenarios that land there — validate before publishing.

**Presets**

- **One milestone per step**, titled as a verb phrase.
- **Scaffold what the preset always creates** (the audit, the perimeter); **point** (no scaffold) at objects the user supplies at run time.
- **Cross-step focus for shared objects** — scaffold once, focus from each step; don't scaffold twice.

**Localisation** — author the base language first; don't translate identifiers (`ref_id`, URN, matrix abbreviation).

## Builder vs Excel

- **Builder** — for content that lives primarily on this instance (internal policies, forked variants, in-progress drafts), for iterative editing, and anywhere a translation pass matters (the side-by-side editing and coverage counter are hard to replicate in a spreadsheet).
- **Excel** — for content you ship as a library file across instances or to the community catalogue, for constructs the builder UI doesn't expose (e.g. per-requirement score overrides), and for the initial conversion of a published standard from its source spreadsheet. See [Excel-driven authoring](excel.md) and [Designing your own libraries](../libraries/custom-libraries.md).

The two paths compose: an Excel-built library can be imported into a draft and tuned in place, and a builder draft can be exported to YAML for redistribution.

## Set the default packager

The packager used to pre-fill new drafts is an instance-wide setting.

- Go to **Settings → General settings** and set **Default packager** (defaults to `custom`). It must match `^[a-z0-9_-]+$`.

Individual users' most recently typed packager is also remembered locally and takes precedence in the quick-create forms.

## Notes and limitations

- **No splash-screen images.** The requirement-node "splash screen" no longer supports uploading an image: images don't travel in library YAML, so they'd break on import elsewhere. Use markdown text for intros and methodology blocks.
- **No respondent preview inside the builder.** The framework editor here doesn't offer the "preview as respondent" view the standalone builder had; publish the library (or a working copy) to see it rendered.
- **Everything is RBAC-scoped.** The builder only shows and resolves against libraries and objects you're allowed to see — including during validation and dependency resolution. You see what you're allowed to see.
- **Migration from the old builders.** In-flight drafts from the previous per-object builders were migrated into draft libraries on upgrade, so existing work is preserved.
- **Author mappings as a separate library**, not inside a framework, and map at the leaf level — section-to-section mappings rarely survive reorganisations. See the [Mappings concept](../../concepts/mappings.md).

## Related

- [Libraries](../libraries/README.md) — how to load, upgrade, and clean up authored content.
- [Excel-driven authoring](excel.md) — the alternative Excel-to-YAML workflow for cross-instance publishing.
- [Designing your own libraries](../libraries/custom-libraries.md) — the library YAML format the builder produces.
- [Getting your custom framework](../libraries/custom-frameworks.md) — quick-start for a single-framework library.
- [Library upgrade](../libraries/library-upgrade.md) — what changes are safe to ship in a later version.
- Concepts: [Frameworks](../../concepts/frameworks.md) · [Risk matrices](../../concepts/risk-matrices.md) · [Journeys](../../concepts/journeys.md) · [Mappings](../../concepts/mappings.md).
- [Contributing → Frameworks and libraries](../../contributing/framework.md) — how to upstream authored content to the community catalogue.
