---
description: Task-oriented recipes for authoring a journey preset — fork, build steps, scaffold objects, publish
---

# Journey preset authoring

A **journey preset** is a reusable template for a journey — the bundle of audits, risk assessments, and supporting objects that a team applies to a new perimeter (e.g. _new project intake_, _supplier onboarding_, _annual ISO recertification_). Authoring a preset well turns repeated set-up work into a one-click instantiation, with consistent naming, owners, and scope across teams. The recommended way to author one is the **in-app preset editor** at **`/experimental/preset-editor`**. This page is a set of task-oriented recipes — find the one that matches what you're trying to do, follow the steps. For the complete walkthrough of every surface in the editor, see [Preset editor — reference](preset-editor.md).

{% hint style="warning" %}
**Experimental.** The preset editor is exposed under the `/experimental/` namespace while its UX is being polished. The URL and menu entry are likely to move once it graduates, and individual surfaces may change between releases. The underlying data stays — your drafts and published presets aren't at risk — but expect occasional rough edges. Feedback is welcome.
{% endhint %}

## Tasks

### Create a blank preset

For designing a journey from scratch:

1. Go to **`/experimental/preset-editor`**.
2. In the **Start something new** card, type a name in the optional **Name** field (e.g. _Vendor onboarding_) — leave blank to default to _Untitled preset_.
3. Click **Create blank preset**. The per-preset editor opens with an empty steps list.
4. Inline-edit the **Preset name** (at the top of the editor) and add a **Description** explaining what the preset is for, who runs it, and when.
5. Add your first step (see [Add a step](#add-a-step) below).

### Fork from a library preset

For starting from a built-in or community preset rather than from scratch:

1. Go to **`/experimental/preset-editor`** and click **Fork from library**. A panel expands listing every library-shipped preset.
2. Find the preset you want to fork and click **Fork** on its card. A fresh editable copy is created and the per-preset editor opens on the clone.
3. The original library preset stays intact — your fork is independent and won't be touched by future library upgrades.
4. Rename, prune, add steps, and tune the scaffolds. **Save** and **Publish** when ready.

### Duplicate one of your presets

For creating a variant (_Light_ / _Full_ flavours, region-specific tweaks):

1. From the preset hub, find the preset in **Your presets** and click **Duplicate**.
2. A fresh editable copy opens with all steps and scaffolds copied.
3. Rename, tune, and publish as a separate preset.

### Add a step

1. In the per-preset editor, click **Add step** in the **Steps** header. A new step card appears at the bottom.
2. Or hover the gap between two existing steps — a thin separator with an **Insert step** label appears; click it to splice a step in at that position.
3. Per step, set:
   - **Title** — the human-readable label users see at instantiation (_"Set up the perimeter"_, _"Run the audit"_).
   - **Description** — optional context.
   - **Key** — the internal identifier (auto-generated as `step_1`, `step_2`, …). Edit if you want a more meaningful key like `perimeter_setup`.

### Have a step land on a specific object — pointer mode

A step can land the user on _something_ when they advance to it. Three modes:

#### Land on an existing model

For taking the user to a list page (e.g. assets, applied controls, evidences) where they'll pick or create their own:

1. In the step card, set the pointer mode to **Model**.
2. In the **Target model** dropdown, pick the model (e.g. `applied-controls`).
3. Leave **Target ref** blank — the user lands on the model's list page.

#### Land on a scaffolded object

For taking the user to a specific object the preset creates (e.g. the audit it spawns):

1. Set pointer mode to **Model**.
2. Pick the **Target model** (e.g. `compliance-assessments`).
3. In the same step, click **Add object** to scaffold a new audit — the new scaffold becomes the step's focus automatically.
4. Or, in the **Target ref** dropdown, pick an existing scaffolded object (including ones owned by other steps, for cross-step focus).

#### Land on a URL

For external SOPs, embedded handbook links, or third-party tools:

1. Set pointer mode to **URL**.
2. In the **Target URL** input, type the URL (relative or absolute).

### Scaffold an audit on a step

When a step should create an audit at instantiation time:

1. Make sure the step's pointer mode is **Model** and **Target model** is `compliance-assessments`.
2. Click **Add object** at the bottom of the step card. A new scaffold card appears.
3. Per scaffold, set:
   - **Ref** — the internal identifier (auto-generated; edit if you want a more meaningful one like `iso_audit`).
   - **Name** — what the spawned audit will be called.
   - **Framework** — pick from the dropdown of loaded framework libraries.
   - **Implementation groups** — once a framework is picked, tick the IGs the audit should scope to. Empty selection means _all requirements_.
   - **Description** — optional.
4. The step's **Target ref** automatically points at this scaffold (the "create and open" pattern).

### Scaffold a risk assessment

Same flow, with a different target model:

1. Step's **Target model** is `risk-assessments` (or `business-impact-analysis` for a BIA, `ebios-rm` for an EBIOS RM study).
2. Click **Add object**.
3. Set **Ref**, **Name**, **Description**, and pick a **Risk matrix** from the dropdown of loaded matrix libraries.

### Scaffold a findings assessment

For pentest / audit / review tracking:

1. Step's **Target model** is `findings-assessments`.
2. Click **Add object**.
3. Set **Ref**, **Name**, **Description**.
4. Pick a **Category**: `pentest`, `audit`, `review`, or `other`.

### Scaffold an asset

For declaring assets the preset will create:

1. Step's **Target model** is `assets`.
2. Click **Add object**.
3. Set **Ref**, **Name**, **Description**.
4. Pick an **Asset type**: `SP` (Support asset) or `PR` (Primary asset).

### Have multiple steps focus on the same scaffold

For a journey where several steps act on the same audit (_"Set up"_ → _"Fill in"_ → _"Sign off"_, all on the same audit):

1. Set up the **first** step: pointer mode **Model**, target model `compliance-assessments`, click **Add object** to scaffold the audit (e.g. `ref: iso_audit`).
2. Add a **second** step. Set its pointer mode to **Model**, target model also `compliance-assessments`.
3. In the second step's **Target ref** dropdown, you'll see `iso_audit` listed (owned by the first step) as a cross-step candidate. Pick it.
4. Repeat for the third step. Now all three steps land the user on the same audit, but each at a different point in the journey.

> When you rename the scaffold's `ref`, the editor automatically updates every step that pointed at it, so refactors stay consistent.

### Add parameters to a scaffold

For seeding additional fields on the spawned object that the editor doesn't otherwise expose:

1. Inside the scaffold card, expand the **Parameters** section.
2. Click **Add row**. Fill in:
   - **Key** — the field name (e.g. `owner`, `priority`).
   - **Value** — the value. Comma-separate for arrays (e.g. `tag1, tag2, tag3`).
3. Save the draft. The parameters apply at instantiation time.

### Reorder or delete a step

1. Use **Move up** / **Move down** on the step card to swap with the adjacent step.
2. Click **Delete step** to remove. If the step owns any scaffolded objects, a confirmation prompt lists them and warns that they'll be removed too. Any other step that focused on a deleted scaffold has its focus cleared.

### Save your draft

1. Click **Save** in the sticky toolbar at the top of the editor. The button is only active when there are unsaved changes.
2. The status pill updates: _Draft_ if you've never published, _Published v{n}_ if the draft now matches live (rare — usually it'll show _Unsaved changes_ between save and publish).

> A `beforeunload` guard prompts before browser tab close or refresh when there are unsaved changes, and SvelteKit's `beforeNavigate` does the same for in-app navigation. Save before walking away.

### Publish your draft

1. Save first — the **Publish** button is disabled while there are unsaved changes.
2. Click **Publish**. The server runs a publish-preview:
   - If no steps are being deleted, the publish happens immediately and the _Published!_ flash appears.
   - If the publish would delete one or more steps from the live preset, a modal lists them. Review carefully — deleting a step from a preset already instantiated in a journey can leave that journey in a broken state.
3. Click **Confirm publish** in the modal to commit. The status pill flips to _Published v{n+1}_.

### Discard a draft

To throw away in-progress edits and start over from the last published state:

1. Click **Discard** in the toolbar. An inline _"Discard draft?"_ prompt appears.
2. Click **Yes, discard**. The server-side draft is deleted and the editor reloads from the live preset (or a fresh blank if the preset has never been published).

### Delete a preset

From the preset hub:

1. Find the preset in **Your presets**.
2. Click **Delete** in the row. A confirmation dialog asks before removing the preset entirely.

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
- If you stored a framework's own URN, that URN may not exist on another instance — but the library URN will, because libraries are designed to be portable.

The editor handles this automatically — you pick from a "loaded library" dropdown, not a "loaded framework" dropdown. The published preset stores the right thing.

### Sharing presets across teams

- **Domain-scoped sharing** — a preset created on one instance is available to every user who has access to it through IAM. Use the preset's folder ownership to control visibility.
- **Forking instead of editing** — when a team wants their own variant of a shared preset, _Duplicate_ produces an independent fork. Edits on the fork don't propagate back to the source, which is usually what's wanted.

## Related

- [Preset editor — reference](preset-editor.md) — every surface and action in the editor.
- [Journeys concept](../../concepts/journeys.md) — what a journey _is_ in the data model.
- [Framework authoring](framework.md) — presets typically reference one or more frameworks you've authored.
- [Risk matrix authoring](matrix.md) — presets typically reference a default matrix.
- [Initial setup](../../guides/initial-setup.md) — the first journey for a fresh instance.
- [Excel-driven authoring](excel.md) — the wider library-YAML workflow.
