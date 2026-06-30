# Library Builder — Design Note

## Summary

The library builder is an **interactive packager**: a tool for authoring a
library (the same artifact the `tools/` Excel convertor produces), edited in the
UI instead of a spreadsheet. It produces a **library YAML**. "Publishing" means
**loading that YAML like any other library** — in this instance or any other,
identically.

It is a *library* builder, not a framework builder: one library can hold any mix
of object types (framework, reference controls, threats, risk matrix, mappings,
presets, metrics).

## Core principles

1. **Single writer = the loader.** The builder never writes live objects
   (`Framework`/`ReferenceControl`/`Threat`/…). The library loader is the only
   thing that materializes live objects, via the existing import path. This
   removes, by construction, the whole class of ownership/authorization bugs
   that came from a bespoke publish path trusting client data.
2. **Draft = a document, not live objects.** Work-in-progress is a structured
   document (serializes to the library YAML), not rows in the live tables.
3. **Ownership is by library, never by framework.** An object belongs to a
   library (`library` FK / its URN family). A framework only *references*
   controls/threats by URN; cross-library links are `dependencies`.
4. **Untrusted input.** The draft is client data; nothing in it is acted on
   until it goes through the loader's existing validation + RBAC scoping.
5. **One signal, one meaning.** `is_published` is the IAM visibility flag only;
   builder lifecycle is the draft state. No overloading.

## Identity

A library's identity is two prerequisite fields (the Excel `library_meta`):

- `packager` — author/org identifier
- `ref_id` — the library's reference id

These deterministically generate the URN family (type token varies, same
`packager`+`ref_id`):

```
urn:{packager}:risk:library:{ref_id}
urn:{packager}:risk:framework:{ref_id}
urn:{packager}:risk:req_node:{ref_id}            (base; nodes append :{node_ref})
urn:{packager}:risk:threat:{ref_id}              (base)
urn:{packager}:risk:reference_control:{ref_id}   (base)
urn:{packager}:risk:matrix:{ref_id}
urn:{packager}:risk:req_mapping_set:{ref_id}
urn:{packager}:risk:preset:{ref_id} | metric:{ref_id}
```

`urn:…:risk:function:…` is the **legacy spelling of `reference_control`**: the
loader keeps recognizing it for existing libraries; the builder mints only
`reference_control`.

Object URNs are pinned to `ref_id`, **never derived from the display name** —
this is what eliminates rename/slug drift.

`packager`/`ref_id` are **freely chosen** — no scoping or namespace restriction.
Loading a library is an act of trust in its packager (you choose to load it),
and **uniqueness is enforced by the existing load-time checks**, not by
constraining the choice up front.

Free choice does not preclude conflict-checking. Two complementary layers:
- **Authoring-time (advisory):** check the chosen identity / URN family against
  the existing `StoredLibrary` set (broader than *loaded* — catches
  stored-but-not-loaded too) and warn. Since identity is editable while a draft,
  the author just renames — a cheap document edit — before publishing.
- **Load-time (enforcing):** the existing uniqueness checks remain the hard gate.

## Lifecycle

```
choose packager+ref_id  →  design objects (draft, identity editable)  →  publish = load (identity frozen)  →  re-edit/re-publish = update-by-URN
```

- **Draft (unpublished):** `packager`/`ref_id` freely editable. Changing either
  regenerates the URN family across the document — cheap and safe because it's a
  document (no live objects, no dependents, no migration).
- **Published (loaded/distributed):** identity is **frozen** and immutable —
  dependencies, mappings, and audits reference it by URN. Re-publishing updates
  the existing library in place via `update_or_create(urn=…)`.
- **Editability** = "still a draft, not yet loaded" — not "`framework.urn IS
  NULL`". The old null-URN editability hack is retired.

## Cloning / extraction

Cloning is **selective extraction**: pick objects from a source `StoredLibrary`
(filter by type — e.g. only reference controls — or individually), copy by
value, and rebase their URNs + internal cross-references onto the draft's
`packager`/`ref_id`. Document → document; never touches live objects. Replaces
the per-type `frameworks/{id}/duplicate` (`_build_urn_map`/`_carry_links`) with
one generic operation.

**Reference integrity.** Only **frameworks** carry references (req_node →
reference_control/threat), so extraction is unconditionally clean for every leaf
type. When a framework is picked and a node reference points *outside* the
selection, resolve it per-reference, chosen by the user at pick time:

| Policy | Effect |
| --- | --- |
| **skip / strip** *(default)* | drop the link → a self-contained framework |
| **pull-in (closure)** | also extract + rebase the referenced object |
| **reference** | keep the original URN + add a dependency on the source library |

(Mappings inherently reference *other* libraries' frameworks → always the
"reference" case.)

Two distinct things, not a "whole-library" operation:
- **Clone** — an explicit *seed/import* action: copy objects by value into your
  library, rebased to your URN; you own and can edit them.
- **Reference** — *not* a separate action but a normal authoring capability:
  when attaching a control/threat to a node, the picker may offer objects from
  external libraries; choosing one records a `dependency` and links by URN. The
  object stays in its library — not copied, not owned, read-only, resolved at
  load. This is exactly CISO's existing `dependencies` mechanism.

  **References are dependency-scoped** (mirrors the Excel `urn_prefix` +
  `dependencies` convention: a reference is written `prefix:ref_id`, where the
  prefix names the source dependency). With multiple dependencies you must
  **select which dependency** an object comes from — different dependencies can
  hold same-`ref_id` objects, so the choice both disambiguates and pins
  provenance. The draft maintains the `dependencies` list and a `urn_prefix`
  entry per dependency; the picker is grouped by dependency; referencing an
  object from an undeclared library **auto-adds the dependency**; on export the
  builder emits the `urn_prefix` map so the YAML uses the compact `prefix:ref_id`
  form, exactly like the `tools/` Excel output.

## Editing existing libraries — adopt vs. clone

Two ways to bring an existing library into the builder, distinguished by whether
its identity is **yours**:

- **Adopt (identity preserved).** Import a library *you own* (e.g. one you've
  been maintaining via the `tools/` Excel pipeline) into a `LibraryDraft`
  **keeping its `packager`/`ref_id`** and all URNs as-is (no rebase). You then
  maintain it in the builder instead of Excel; publish = load =
  `update_or_create(urn=…)` updates it in place. This is the inverse of publish
  (YAML → draft).
- **Clone (identity rebased).** Import a library you *don't* own into a draft
  under a *new* `packager`/`ref_id` (the selective-extraction flow above).

Editability rule, keyed on the existing **`builtin`** flag (`LibraryMixin`, on
both `StoredLibrary` and `LoadedLibrary`):

| Library | `builtin` | Builder offers |
| --- | --- | --- |
| Shipped with the product | `True` | **Clone only** (read-only — never Adopt: it isn't your packager); its controls/threats can still be **referenced** |
| Custom (uploaded / builder-published) | `False` | **Adopt** (keep identity) *or* **Clone** (fork) |

Equivalently: **editable-in-builder = there is a `LibraryDraft` you control.** A
built-in can never acquire an identity-preserving draft. Note `builtin` is a
product-origin marker, **not** a hard security boundary (a user can upload a
non-builtin library with the same URN — see `core/models.py`), which is fine for
gating *workflow*; the real trust/uniqueness boundary is enforced at **load**.

**Requirement:** Adopt (and the publish round-trip) demands the builder's
document model **losslessly represent the full library YAML schema** for every
object type — otherwise import would silently drop constructs Excel can express.
Round-trip parity (YAML → draft → YAML) is a hard correctness requirement.

## Storage

Work-in-progress lives in a **dedicated `LibraryDraft` model** (decided)
— `{name, folder, packager, ref_id, content (JSON), updated_at}` — **not** as
live object rows, and **not** as a flagged `StoredLibrary`. A flag would re-
overload `StoredLibrary` ("immutable loadable artifact" vs. "mutable draft")
across its ~90 call sites and 35 query sites; a dedicated model (~200 lines of
concentrated scaffolding, reusing the existing import/load logic via publish)
keeps that meaning clean. On publish, the draft produces a `StoredLibrary` fed
to the existing `import_stored_library` path. `editing_draft` is already a
document blob — the change is to stop *also* materializing live objects /
keeping a live `Framework` row during editing.

## What this replaces / consolidates

- The current framework builder's bespoke `publish-draft` reconcile against live
  tables (and its client-ID-trusting upserts).
- The separate per-type editors that each reinvent
  `editing_draft`/`editing_version`/`is_published`/publish (risk-matrix visual
  editor, presets) — they collapse onto this one model.
- `frameworks/{id}/duplicate` → the generic clone/extract operation.

## Open decisions

(none — see resolved decisions below.)

> Draft storage (resolved): a **dedicated `LibraryDraft` model**, not a flagged
> `StoredLibrary` — keeps `StoredLibrary`'s single meaning intact.
>
> Publish path (resolved): routes through the exact existing
> `import_stored_library` path — one writer, already validated and RBAC-scoped.
>
> Clone vs. reference (resolved): **Clone** is an explicit copy/fork import
> action; **referencing** external controls/threats is a normal authoring
> capability (picker → `dependency` + URN link), not a separate "extend"
> action.

> URN choice is **not** restricted (resolved): `packager`/`ref_id` are freely
> chosen; trust is established by loading; uniqueness is enforced by existing
> load-time checks — plus an advisory authoring-time check against the existing
> `StoredLibrary` set so conflicts surface while the draft is still cheap to
> rename.
>
> Built-in editability (resolved): built-in libraries (`builtin = True`) are
> read-only in the builder — customize via Clone/Extend, never in place.
> Custom libraries can be Adopted (identity preserved) or Cloned.
