# Mapping-set editor for the library builder: implementation plan

Worktree `.claude/worktrees/mapping-editor`, branch `worktree-mapping-editor`, from `main` at c47c22ddf5.

## Starting point

- UX decisions from 2026-10-19 (primer + mocks canvas, see memory `project_mapping_builder_ux`). The chosen surface is **A′**: one row per source requirement, a target autocomplete on each row, and obvious cases pre-filled as unconfirmed chips that the author confirms in batch.
- Today mapping sets only get into a draft through YAML import (`import-objects`). The builder page shows them read-only with a delete button (`[id=uuid]/+page.svelte:1563`). `UPSERTABLE_FIELDS` leaves them out on purpose ("mapping sets have their own tooling", `backend/library/views.py:1094`).
- Validation already covers them: shape (`builder.check_document_shape`, `builder.py:261`), framework refs (`_check_reference_integrity`, `builder.py:1191`), and delete-blocking when a set points at a framework. Export/publish already carries `content.requirement_mapping_sets`. **Neither the loader nor the YAML shape changes.**

## Decisions (2026-11-26)

- Manual adds default to `intersect`.
- Frameworks are read from draft content + `StoredLibrary.content` (covers loaded and stored-only). If that path turns out to complicate things, fall back to loaded frameworks only.
- The builder create form gets a "Mapping library" starting point.
- **Headline basic case: a customer clones a builtin framework, changes its URN and rewords the items.** The rewording means name matching fails, so suggestions must key on structure, not text (see below).

### Why the clone case is cheap

Cloning goes through `import-objects` → `build_urn_map` (`backend/library/builder.py:313`): the framework gets `{draft base}:{ref_id leaf}`, and every requirement node is remapped by **prefix substitution**. So a clone's node URN keeps the original's tail after the framework segment (`…:req_node:iso27001-2022:a.5.1` → `…:req_node:acme-isms:a.5.1`), whatever the author did to names and descriptions afterwards. The framework `ref_id` is usually kept too. Clone provenance is not recorded anywhere, so the original is **detected**, not looked up.

The mapping graph is directional (`MappingEngine.framework_mappings`, `backend/core/mappings/engine.py:95`). The clone needs **both** directions: clone→builtin so the customer's audit feeds every framework reachable from the builtin, and builtin→clone so existing builtin audits can prefill the clone. That is why the reverse set is in slice 1.

## Slice 1 (MVP): the basic cases with as few clicks as possible

### Backend (`backend/library/views.py`, `LibraryDraftViewSet`)

1. `GET  mapping-frameworks`: the frameworks an author can pick: the draft's own plus those of readable stored libraries (`accessible_stored_library_ids`). Each entry gives `{urn, name, library_urn, assessable_count}`. Built the same way as `reference_catalog`.
2. `POST add-mapping-set {source_framework_urn, target_framework_urn}`:
   - mints `urn:{packager}:risk:req_mapping_set:{ref_id}` through `leaf_object_base`, with default name `"<src> ↔ <tgt>"`;
   - auto-declares both owning libraries in `dependencies`, reusing the `find_owning_library_urn` / `find_stored_owner_urn` path from `_sync_link_dependencies`;
   - rejects source == target and an already existing pair.
3. `GET  mapping-editor?set_urn=`: returns the set's metadata, its pairs, and the **assessable** nodes of both sides as `{urn, ref_id, name, description, parent_label}`, read from the draft content or the stored library content (no live Framework rows needed). One payload, so the client can search with no round-trips. SCF is about 1.4k nodes, which is fine.
4. `POST edit-mapping-pairs {set_urn, ops:[{op: add|update|remove, source, target, relationship?, strength_of_relationship?, rationale?, annotation?}]}` (the name the user picked):
   - keyed by `(source, target)`; all ops applied atomically or none;
   - validates that both URNs are assessable nodes of the set's frameworks, that `relationship` ∈ {equal, subset, superset, intersect, not_related}, that `rationale` is in the enum (syntactic/semantic/functional, see memory `reference_mapping_rationale_enum`), and that strength is an int;
   - responds with `{status, count}` only, and does **not** echo `LibraryDraftReadSerializer`, which is too heavy for 6k-pair sets.
5. `GET  mapping-suggestions?set_urn=`: LLM-free, deterministic, unmapped sources only. Arms in priority order (first hit wins per source):
   - same node URN tail after the framework segment → `equal` (the clone signature, immune to rewording);
   - same normalized `ref_id` → `equal` (clones whose tails drifted, version-to-version updates);
   - same normalized name → `equal`;
   - one-to-one only: a target already claimed by a higher arm is not offered again.
   - (slice 2) composition through existing mapping sets via a pivot (e.g. A→SCF→B), which reached about 35% recall@10 in the October bench.
   Each suggestion carries `reason: ref_id|name|pivot:<set urn>` so the chip can say why.
6. `GET  mapping-original?framework_urn=`: "is this a clone, and of what?". Candidates are stored frameworks with the same `ref_id`, plus stored frameworks scored by assessable URN-tail overlap. Returns the best one with a score above a fixed threshold (e.g. ≥ 60% of the clone's assessable nodes), or nothing.
7. `add-mapping-set` takes `with_reverse: true`. `POST generate-reverse-set {set_urn}` (re)builds B→A from A→B: swap sides, `subset`↔`superset`, everything else kept. It overwrites the reverse set, so it is derived on demand and never edited in parallel.
8. Register the actions in `permission_map` (view vs change, like `framework_editor`).

Tests in `backend/library/tests/test_library_builder.py`: **clone round-trip** (clone a small stored framework via `import-objects`, reword names → `mapping-original` finds it, URN-tail suggestions cover every assessable node); reverse set swaps subset/superset; create set + deps declared; add/update/remove; duplicate add is idempotent; unknown or non-assessable URN → 400; bad enum → 400; source == target → 400; suggestions on two tiny frameworks; validate + export round-trip still clean.

### Frontend

- New route `experimental/library-builder/[id=uuid]/mapping/` (`+page.server.ts`, `+page.svelte`, `+server.ts` proxy) using the `matrix/` sub-editor pattern.
- **Builder page, framework card**: when `mapping-original` finds a match, show **"Map to <original name>"** (both directions ticked by default). One click creates both sets and opens the editor with every node pre-suggested.
- **Builder page**: a "New mapping set" button opens a modal with two framework pickers and a swap button, then goes straight to the editor. Existing set cards get an "Edit" link.
- **Editor layout (A′)**:
  - Header: `source ⇄ target`, progress (`312 / 590 mapped`), and filters: search, *unmapped only*, section.
  - One row per source requirement, showing ref_id + name, with the description in a tooltip or on expand.
  - Mapped targets as chips. Clicking a chip cycles the relationship (`intersect → equal → subset → superset`), and × removes it. The chip is coloured by relationship.
  - Suggestions as dashed chips: ✓ accepts one, and the header has **"Accept all N suggestions"**.
  - Per-row target autocomplete: client-side match on ref_id + name + description, Enter adds it with the default relationship (`intersect`, editable in the header).
- **Keyboard-first**: `j/k` or ↑/↓ move between rows, `/` focuses search, typing on a row opens its autocomplete, `a` accepts the row's suggestions, `Ctrl+Z` undoes.
- **Saving**: ops are queued and flushed in batches (debounced) to `edit-mapping-pairs`. Undo pushes the inverse op, which is computed client-side from the previous pair state. Last save wins.
- i18n keys go in `messages/en.json` + `fr.json`, and are reused where labels already exist (`lbCountRequirementMappingSets` etc.).
- Also check `enterprise/frontend` for shadowed builder files (memory `feedback_always_check_enterprise_frontend`).

Expected flows:
- **Clone of a builtin:** "Map to ISO 27001:2022" → editor opens, all nodes suggested `equal` → "Accept all" → retag the few nodes whose meaning actually changed (chip click → `subset`/`intersect`) → "Regenerate reverse" → Publish. About 4 clicks plus the real review work.
- **Version upgrade / other pair:** New mapping set → pick 2 frameworks → "Accept all" on ref_id/name matches → fill the leftovers with the autocomplete.

## Slice 2

- Pivot composition suggestions through shipped mapping sets (`MappingEngine.load_rms_data` reads `StoredLibrary.content`).
- A "Nothing maps" mark and rejected suggestions, so the *unmapped only* filter converges. This needs the draft-only authoring meta field beside `content`, which is never exported (decision 2026-10-19), plus one migration.
- Reverse view (rows = target).
- Record clone provenance at `import-objects` time (draft-only meta) instead of detecting it.
- Optional TF-IDF suggestion arm (stdlib, still LLM-free).

## Out of scope

AI/embedder suggestions (`project_mapping_assistant`), "reviewed by", and fixing defects in shipped mapping data (strength 50/90, free-text rationale), which is a separate PR.

## Open points

- Should "Accept all" on a clone default to `equal` for nodes whose description changed a lot? A cheap text-distance flag could mark those chips "reworded, check" without changing the relationship. Lean: flag only, never auto-downgrade.

## Status 2026-11-26: slice 1 built (uncommitted)

- Backend: `backend/library/mapping_editor.py` (pure logic) + six `LibraryDraftViewSet` actions: `mapping-frameworks`, `mapping-original`, `add-mapping-set`, `mapping-editor` (suggestions included in this payload, so there is no separate `mapping-suggestions` endpoint), `edit-mapping-pairs`, `generate-reverse-set`. Tests: `backend/library/tests/test_mapping_editor.py`.
- Clone detection ranks stored frameworks by fuzzy name closeness (an exact ref_id wins), then scores the 10 closest by URN-tail overlap. A real clone ("NIST CSF v2.0 (copy)") had no framework ref_id and a renamed title, so exact matching missed it.
- Frontend: `[id=uuid]/mapping/` editor, `FrameworkPicker.svelte`, the "Map to <original>" button on the framework card, the "New mapping set" panel, Edit links on sets, and the "New mapping" quick start (lands on the draft with the panel open).
- Checked in the browser on a real NIST CSF 2.0 clone: detected the original → 106 suggestions → Accept all → cycle a chip / add a target / Ctrl+Z → reverse generated → validate clean.
- Not checked in the browser: the quick start and the New mapping set panel (the session cookie expired), and the reworded flag (the clone wasn't reworded; it is covered by tests).

## Status 2026-11-26: stored-mapping suggestions built (uncommitted)

- Direct: a stored mapping set linking both frameworks (either direction) is offered as is, reason `mapping`. When one exists, nothing is chained on top.
- Chained: A→P→B through at most 5 pivots, reason `via`. Only provable chains: equal∘x = x, subset∘subset, superset∘superset; overlap∘overlap gives nothing; pivots that disagree fall back to intersect.
- A draft framework stands in for its detected original (URN-tail translation), so a clone inherits every shipped mapping of the original.
- Stored mapping libraries are indexed from content via KT (first two sets only), then only the needed ones are loaded.
- Picker: AutocompleteSelect single mode; the draft's own framework reads "· this library".

## Status 2026-11-27: wording hints + consistency checks built (uncommitted)

- Wording hints: TF-IDF cosine on name + description (numpy, no new dependency), top 3 above 0.1, shown in the add box when nothing is typed. Measured on 51 same-language shipped mapping sets: a right target is in the top 3 for 57% of items (median; CSF→ISO 46%, CMMC→CSF 37%, version-to-version ~99%). Different languages score 0, so they show nothing. Speed: median 15 ms, worst 152 ms (1,482 × 1,567 items).
- Consistency checks (mapping_editor.mapping_issues): pairConflict, pairNodeMissing, reverseConflict are errors in Validate; pairDuplicate and equalFanOut are warnings. The editor shows them in a banner, an "Issues only" filter and a row icon, refreshed after every save and reverse generation.
