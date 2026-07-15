---
description: Author a whole library — frameworks, matrices, threats, controls, presets — as a draft document, then publish it through the standard loader
---

# Library builder

The **Library builder** is the single place to author library content in CISO Assistant. It lives at **`/experimental/library-builder`** and replaces the earlier per-object builders (framework, matrix, preset): they are now surfaces _inside_ one builder rather than separate tools.

You edit a **draft document** — a `LibraryDraft` — not live database objects. Think of it as a spreadsheet editor for a library: you assemble frameworks (with requirement trees that can reference reference controls and threats), risk matrices, threats, reference controls, and journey presets into one draft, and nothing touches the live catalog until you **publish**. Publishing hands the draft to the **standard library loader** — the same code path that imports any built-in or community library — so authored content behaves exactly like everything else: versioned, upgradable, exportable.

Because a draft serializes to a plain library **YAML**, you can also export it and re-import it on another instance, or import an existing library YAML straight into a new editable draft.

{% hint style="warning" %}
**Experimental.** The library builder is exposed under the `/experimental/` namespace while its UX is being polished. The URL and menu entry may move once it graduates, and individual surfaces may change between releases. Your drafts and published libraries are not at risk. Feedback is welcome.
{% endhint %}

## Concepts in one minute

- **Draft (`LibraryDraft`)** — the working document. Editing a draft never mutates live objects.
- **Identity** — a library is identified by its **packager** and **ref_id** (e.g. `packager = acme`, `ref_id = my-policy`). Every URN in the library derives from them: `urn:acme:risk:framework:my-policy`. Identity is **editable while the library is a draft** and **frozen on first publish** — renaming a draft rewrites the whole URN family for you; once published, it's locked.
- **Publish** — loads the draft through the standard loader. Re-publishing a library you've edited upgrades the loaded objects in place, by URN.
- **Adopt** — bring an existing custom library (or a library-less framework left by the old builders) into a draft so you can keep editing it.

## Tasks

### Author a single framework or matrix (simple mode)

For the common case — one framework, or one matrix, with no other objects — you don't need to think about libraries at all.

1. Go to **`/experimental/library-builder`**.
2. Click **New framework** or **New matrix**.
3. Enter a **name** and a **packager** (your namespace, e.g. `acme`). The packager is remembered after the first time, and the default can be set instance-wide (see [Set the default packager](#set-the-default-packager)).
4. Click **Create & edit**. The wrapping library is minted behind the scenes — its ref_id is slugged from the name and de-duplicated against your corpus — and you land straight in the object's editor.
5. Edit as usual, then publish.

The draft page shows a **simple view** for single-object libraries and a toggle to the **full view** when you need the library-level surfaces.

### Author a full library (multiple objects)

1. Go to **`/experimental/library-builder`** and click **New Library Draft**.
2. Set the **name**, **packager**, and **ref_id**. The assembled URN previews live below the inputs, and an identity check warns if it collides with an existing library or object.
3. Click **Create**. You land on the draft page in full view.
4. Add objects from the draft page:
   - **Framework** — opens the framework editor (requirement tree, scoring, implementation groups, and node-level references to reference controls and threats).
   - **Risk matrix** — opens the matrix editor (grid, palette, translations).
   - **Threats** and **Reference controls** — table editors for the catalog objects a framework can reference.
   - **Preset** — a journey preset that scaffolds objects for a recurring assessment.
5. Save as you go. The draft's **Contents** column summarizes what it holds (e.g. _1 framework, 2 threats_).
6. Publish when ready.

### Reference reference controls and threats from a requirement

Inside the framework editor, a requirement node can point at reference controls and threats. The picker offers the objects available to the draft — those defined in the same draft, plus objects from libraries the draft **depends on**. Picking an object from another library automatically records the dependency so the reference resolves at load time.

### Import an existing library YAML

To start from a YAML file rather than the corpus:

1. On the builder list, click **Import YAML** and choose a `.yaml` / `.yml` file.
2. The file is parsed and validated, and a **new editable draft** is created from it.
3. The **packager and ref_id remain editable** (the draft is not published), so you can rename the identity — renaming rebases the whole URN family — before publishing under your own namespace.

### Adopt a custom library

To keep editing a library that's already loaded:

1. On the builder list, pick the library from the **Adopt a custom library…** select and click **Adopt**.
2. A draft is created that keeps the library's identity. Editing and re-publishing upgrades the loaded objects in place.

Library-less frameworks left by the retired standalone builder appear in the same select under **Custom frameworks (no library yet)** and can be adopted the same way.

### Clone objects from another library or draft

When building a new draft, you can copy objects **by value** from an existing source:

1. In the draft, use the **import / clone** source select. It groups **loaded libraries** and your other **drafts**.
2. Pick the source and the objects to copy. They are copied into the current draft and **rebased** onto its URN family, so the clones belong to your library and evolve independently of the source.

### Delete an object from a draft

Each framework, matrix, and preset card in the full view has a **delete** button. Deleting removes the object from the draft document only — it doesn't touch anything live. A framework that is still referenced by a mapping set in the same draft is protected from deletion.

### Set the default packager

The packager used to pre-fill new drafts is an instance-wide setting.

- Go to **Settings → General settings** and set **Default packager** (defaults to `custom`). It must match `^[a-z0-9_-]+$`.

Individual users' most recently typed packager is also remembered locally and takes precedence in the quick-create forms.

## Notes and limitations

- **No splash-screen images.** The requirement-node "splash screen" no longer supports uploading an image: images don't travel in library YAML, so they'd break on import elsewhere. Use markdown text for intros and methodology blocks.
- **Everything is RBAC-scoped.** The builder only shows and resolves against libraries and objects you're allowed to see — including during validation and dependency resolution. You see what you're allowed to see.
- **Migration from the old builders.** In-flight drafts from the previous per-object builders were migrated into draft libraries on upgrade, so existing work is preserved.

## Related

- [Libraries](../libraries/README.md) — how to load, upgrade, and clean up authored content.
- [Framework authoring](framework.md) · [Risk matrix authoring](matrix.md) · [Journey preset authoring](preset.md) — object-specific recipes and the deep-reference subpages for each editor surface.
- [Designing your own libraries](../libraries/custom-libraries.md) — the library YAML format the builder produces.
- [Excel-driven authoring](excel.md) — the alternative Excel-to-YAML workflow for cross-instance publishing.
