# IAM module — target architecture & phased plan

**Baseline:** branch `feat/use_queryset_for_iam` (queryset-based IAM decisions + `Folder.descendants` closure).
**Companion doc:** `iam-queryset-pr-review.md` (Phase 0 findings in detail).
**Date:** 2026-07-17
**Status:** proposal — Phase 0 pending, phases 1–5 sequenced behind it.

---

## 1. Design principles

1. **The IAM API keeps its established shape.** Same `RoleAssignment` static-method namespace and style — no manager/queryset API on models (rejected as too large a departure). One deliberate evolution: the single-perm verb `get_accessible_ids(user, perm_prefix, model)` replaces the `(view, change, delete)` triplet; `get_accessible_object_ids` survives only as a transitional wrapper during migration and is **deleted at the end of Phase 3**.
2. **One algebra.** Exactly one function knows the flat-vs-recursive expansion, the closure, and focus mode: `get_allowed_folder_ids`. Every verb is a thin composition over it. The flat/recursive semantics are never implemented twice.
3. **Granted ≠ readable.** `get_allowed_folder_ids` answers "where is this permission *granted*" and stays publish-free for all perms. Published visibility is a *view-only* overlay composed above it. Write checks must be structurally unable to see published folders.
4. **One derived structure.** The `descendants` closure is the single materialization of the folder tree. The in-memory snapshot cache is removed, not maintained in parallel.
5. **The spec is executable.** A conformance matrix suite asserts list / retrieve / write agreement for every semantic dimension. Any future change that makes two paths disagree fails CI.

---

## 2. Target architecture

```
principal resolution      get_role_assignments_from_user(user)
                            direct ∪ via groups ∪ via IdP groups (flag-gated)
                                      │
permission filter         get_role_assignments_from_permission(user, perm_prefix, model)
                            + internal path: filter(role__permissions=perm) for exact
                              Permission objects (no codename string surgery)
                                      │
folder-scope resolver     get_allowed_folder_ids(user, perm_prefix, model, *, base_folder=None)
  (THE crux)                flat perimeters ∪ recursive perimeters × closure
                            focus mode; root fast-path; publish-free
                                      │
                          ┌───────────┼──────────────────────┐
view-only overlay         │   published visibility           │
                          │   (object-level Q today;         │
                          │    folder-set function            │
                          │    `published_folder_ids` after   │
                          │    publication rules — Phase 5)   │
                          └───────────┼──────────────────────┘
                                      │
public verbs (frozen)     is_access_allowed(user, perm, folder)
                          is_object_readable(user, model, id) → is_object_accessible
                          get_accessible_ids(user, perm_prefix, model)     # single-perm bulk verb
                          get_permissions_per_folder / get_permissions /
                          has_permission_anywhere                          # querysets after Phase 4
                                      │
model→folder contract     one declarative mapping per model (default: "folder";
                          Folder: "id"; derived scopes: "risk_assessment__folder", …)
                          consumed by BOTH the queryset path (get_iam_folder_field)
                          and the instance walk (Folder.get_folder)
                                      │
special models            internal dispatch, not inline branches in every verb:
                          Permission → static read-only allowlist
                          FilteringLabel → all-or-nothing per perm
                          Actor → union of User/Team/Entity delegates
```

**What no longer exists at the end:** `iam/cache_builders.py`, `iam/snapshot_cache.py`, the `apps.py` invalidation wiring, `CacheVersion`, all `invalidate_*` calls (~800 lines); per-object `is_published` columns, `PublishInRootFolderMixin`, all forced-publish hooks; hand-rolled folder-chain logic in `is_object_accessible`; codename `split("_")` surgery; per-check `Permission.objects.get()` round-trips; `_user_can_view_all`'s hand-maintained mirror of the verb semantics; the `get_accessible_object_ids` triplet itself (replaced by `get_accessible_ids`).

**What deliberately stays:** the RBAC data model (Role / RoleAssignment / perimeter folders / `is_recursive`); enforcement placement (list gate in `get_queryset`, create gate in serializers, object gate in `RBACPermissions`); the closure M2M (a materialized-path column is a back-pocket alternative, not planned); the respondent restrictive overlay; the global-admin axis (`is_admin`, group-membership based).

---

## 3. Public API freeze

| Function | Status |
|---|---|
| `RoleAssignment.is_access_allowed(user, perm, folder)` | frozen — keeps accepting `Permission` objects; internal normalization |
| `RoleAssignment.is_object_readable(user, model, id)` | frozen |
| `RoleAssignment.get_accessible_ids(user, perm_prefix, model, *, base_folder=None)` | **new** — single-perm object-ID verb, signature mirrors `get_allowed_folder_ids`; the bulk verb of the target API |
| `RoleAssignment.get_accessible_object_ids(folder, user, model)` | **transitional** — reimplemented in Phase 2 as a three-call wrapper over `get_accessible_ids`, deleted at the end of Phase 3 once internal and external call sites have migrated |
| `RoleAssignment.get_allowed_folder_ids(user, perm_prefix, model)` | frozen (new in baseline PR; prefix param renamed in Phase 0 while the function is unreleased) |
| `RoleAssignment.get_permissions_per_folder / get_permissions / has_permission_anywhere` | frozen signatures — reimplemented on querysets in Phase 4 |
| `Folder.get_root_folder / get_sub_folders / get_parent_folders / get_folder_full_path / get_folder` | frozen signatures — cache-free implementations in Phase 4 |
| `Model.objects.for_user(...)` manager API | **rejected** — too large an API departure |

Terminology: `perm` always denotes a `django.contrib.auth.models.Permission` instance (as in `is_access_allowed`); prefix arguments are named `perm_prefix: PermissionPrefix` (`"view" | "change" | "delete" | "add" | …`). No parameter named `perm` may hold a prefix.

Signature convention: no positional parameters with default values — required arguments are positional, optional arguments are keyword-only (e.g. `*, base_folder=None`). `get_allowed_folder_ids` already complies; new verbs follow suit.

Note: if a genuine all-three-perms consumer ever appears (e.g. a per-row capabilities endpoint), batch at the folder layer (one `(perimeter_folder, codename)` query + one shared closure expansion) in code composing `get_accessible_ids` — not a reason to resurrect the triplet. Today no call site consumes more than one perm.

---

## 4. Phases

### Phase 0 — make the baseline PR safe to merge (~1 day)

Correctness only; full detail in `iam-queryset-pr-review.md`.

- Fix the focus-mode `TypeError` (`in` on a related manager).
- Route `is_object_accessible` through `get_allowed_folder_ids` — kills the non-recursive read escalation, the list/retrieve published divergence, and the ungated published overlay in one change.
- Gate IdP-group grants on `ff_is_enabled("idp_groups")`.
- Exclude `descendants` from `FolderReadSerializer` (+ audit other `__all__` serializers over Folder).
- Restore `is_authenticated` guard in `is_access_allowed`; null-scope guard in `get_iam_folder_id`; filter `role__permissions=perm` directly (removes codename surgery, fixes custom-codename downgrades).
- Root fast-path in `get_allowed_folder_ids`; hoist `get_iam_folder_field` out of the perm loop; trim the per-save full-instance fetch in the closure maintenance.
- Naming pass while the functions are unreleased: reserve `perm` for `Permission` instances; rename prefix parameters to `perm_prefix` (`get_allowed_folder_ids`, `get_role_assignments_from_permission`, `is_object_accessible`, actor/label helpers).
- Targeted regression tests (7, listed in the review doc).

**Exit:** review findings closed; list/retrieve parity pinned by tests; PR mergeable.

### Phase 1 — conformance suite (~1–2 days)

The executable spec, written **before** any further refactoring:

- Matrix: {flat, recursive} × {direct folder, descendant, ancestor, sibling, enclave} × {published, unpublished} × {focus on/off} × {direct user, via group, via IdP group ± flag} × {plain model, derived-scope model, Folder, Actor, FilteringLabel, Permission}.
- For each cell, assert agreement of: list membership, retrieve, write authorization, and (where applicable) related-field masking.
- Query-count budgets on the hot endpoints (list, retrieve, current-user) with `assertNumQueries`, so later phases can't silently regress performance.
- SQLite query-plan sanity check for the composed `IN (SELECT … UNION …)` shapes if SQLite deployments remain supported.

**Exit:** suite green on the Phase 0 baseline; becomes a merge gate for phases 2–5.

### Phase 2 — internal consolidation behind the frozen API (~1–2 days)

- Extract the folder-expansion core into a helper taking an assignments queryset; `get_allowed_folder_ids` and the exact-`Permission` path of `is_access_allowed` share it.
- One model→folder contract: a single declarative mapping (default `"folder"`, explicit for the ~7 derived-scope models), consumed by both `get_iam_folder_field` (queryset path) and `Folder.get_folder` (instance walk). Inventory pass to reconcile the two lists — models where they disagree today (`perimeter`, `processing`, `solution__provider_entity`) get explicit entries and a decision each.
- Special-model dispatch: one internal registry (or cleaned branch block) consulted by the verbs; `is_object_accessible` and `get_accessible_object_ids` lose their duplicated `if model is X` logic.
- Published overlay isolated behind one internal function (still row-flag based) — the seam Phase 5 swaps.
- Introduce `get_accessible_ids(user, perm_prefix, model, *, base_folder=None)`; reimplement `get_accessible_object_ids` as a transitional three-call wrapper over it.

**Exit:** conformance suite green; every verb is a composition over the crux; zero duplicated semantics; existing API behavior byte-identical.

### Phase 3 — migrate internal call sites to the single-perm verb (~1–2 days, mechanical)

- ~187 triplet call sites move to `get_accessible_ids`: `(ids, _, _) = get_accessible_object_ids(root, user, M)` → `ids = get_accessible_ids(user, "view", M)`.
- Wide but shallow diff; the conformance suite and existing API tests carry it. Reviewable as pure find/replace-shaped changes.
- Coordinate the same migration for consumers outside this repo (enterprise modules, integrations) in the same release window, then **delete `get_accessible_object_ids`**.

**Exit:** no caller of `get_accessible_object_ids` remains anywhere; the function is removed from the codebase.

### Phase 4 — remove the snapshot cache (~1–2 days, net ≈ −800 lines)

- Convert the last cache clients to querysets, same signatures:
  - `has_permission_anywhere` → `exists()` over `get_role_assignments_from_user`.
  - `get_permissions` → one `Permission` query via `role__in`.
  - `get_permissions_per_folder` → flat pairs + one closure join for recursive assignments (1–2 queries).
  - `_user_can_view_all` → `not Folder.objects.exclude(id__in=allowed).exists()` — stops hand-mirroring verb semantics.
  - `Folder.get_sub_folders` → closure query; `get_parent_folders` / `get_folder_full_path` → parent-pointer walk (preserves **nearest-first** ordering that `audit_inheritance` depends on; closure M2M is unordered).
  - `Folder.get_root_folder` → direct indexed query + module-level ID memo (root is immutable after bootstrap); the `CacheNotReadyError` migration dance disappears.
  - `PathField` list serialization → request-scoped folder map (one query per request) or recursive CTE; the existing `select_related("folder__parent_folder")` hints only cover 2 levels.
- Delete: `cache_builders.py`, `snapshot_cache.py`, `apps.py` m2m invalidation wiring, `CacheVersion` model + drop migration, `invalidate_*` calls in the four `save()/delete()` overrides, `global_settings/serializers.py`, and test fixtures.

**Exit:** conformance suite + query budgets green; no `iam.snapshot_cache` import anywhere; the closure is the only derived structure.

### Phase 5 — publication rules per (domain, object type) (~2–4 days + product alignment)

Replaces the per-object `is_published` flag. **Gated on product decisions** (§6).

- New model: `PublicationRule(folder, content_type, published)` — sparse overrides on top of code-level per-type defaults (today's `default=True` models *are* the default matrix). Resolution: explicit rule > type default > deny.
- Introduce the second folder-set function: `readable_folder_ids(user, model) = granted("view") ∪ published_folder_ids(user, model)` (non-enclave ancestors carrying a published rule). View paths compose it; every other perm keeps composing `get_allowed_folder_ids`. Publish never enters the granted set.
- Swap the Phase 2 overlay seam from row-flag `Q` to the rules function — the last row-level predicate in the decision layer disappears.
- Remove: `is_published` columns (one wide mechanical migration), serializer fields and UI badges, `PublishInRootFolderMixin`, `Folder.save` force-publish, `ActorSyncManager` force-publish hooks.
- Data migration: rule = `published` iff any published object of that type exists in that folder — **preserves all existing access, may widen visibility to previously-unpublished siblings**. Ship with a pre-migration report listing every (folder, type) that loosens, for admin review.
- Decide the RAG filter semantics: `chat/rag.py` currently uses granted-only folders; under rules, published ancestor content (root catalogs users can open in the UI) should probably move to `readable`.

**Exit:** conformance suite updated to rules semantics and green; no `is_published` reference outside migrations; view/change/delete fully symmetric at the object layer.

---

## 5. Cross-cutting workstreams (cheap, any phase)

| Item | Rationale |
|---|---|
| `manage.py check_iam_closure` | Verifies `descendants` against `parent_folder` pointers; run in CI. The closure is ground truth for every decision; this guards the `QuerySet.update(parent_folder=…)` bypass class and any future maintenance bug. |
| `explain_access(user, obj)` debug helper | Once the algebra is one function, "which assignment grants/denies this, via which folder" is a ~20-line by-product — the most useful support tool an IAM module can have. |
| Cycle guard test | Reparenting a folder under its own descendant must be rejected; verify a guard exists (serializer or save path), add one if not. |

---

## 6. Open decisions

| Decision | Owner | Blocks |
|---|---|---|
| Publication granularity: is dropping per-object publish acceptable, or do real workflows toggle individual objects? | product | Phase 5 |
| Default publication matrix (which types are published-by-default from root — candidate: today's `default=True` set) | product | Phase 5 |
| Migration loosening policy (auto rule-up with report vs manual resolution of mixed folders) | product + ops | Phase 5 |
| RAG folder filter: granted vs readable | product | Phase 5 (edge) |

---

## 7. End-state acceptance criteria

- One implementation of flat/recursive semantics; grep for `is_recursive` in decision code returns exactly one function.
- API evolution is contained: `get_accessible_object_ids` behaves identically through Phases 0–2; Phase 3 migrates all callers (internal + coordinated external) and removes it. No other public signature changes across the plan.
- Zero row-level predicates in the decision layer (post Phase 5); `granted` and `readable` are two named folder-set functions, publish in exactly one of them.
- No IAM snapshot cache; `check_iam_closure` green in CI.
- Conformance matrix green; query budgets on list / retrieve / current-user endpoints enforced.
- Decision layer (resolver + verbs + dispatch + overlay) readable in one sitting: target ≤ ~400 lines in one module.

**Total estimated effort:** ~2 weeks spread over 6 independently landable PRs, front-loaded with the security fixes (Phase 0) and behavior-preserving thereafter under the conformance suite.
