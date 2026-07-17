# Review report — `feat/use_queryset_for_iam`

**Scope:** IAM refactor replacing the in-memory snapshot-cache traversal with database querysets backed by a new materialized `Folder.descendants` closure (M2M, `related_name="ancestors"`).
**Diff:** ~+692/−378 across 11 files; core of the change in `backend/iam/models.py` (+901 modified lines).
**Date:** 2026-07-17
**Verdict:** Sound direction and structure. The list-path algebra (`get_allowed_folder_ids`, `get_accessible_object_ids`) correctly preserves flat-vs-recursive semantics. **Four issues must be fixed before merge**, two of them security-relevant, one a crash.

---

## Findings summary

| # | Severity | Finding | Location |
|---|----------|---------|----------|
| 1 | 🔴 Blocker | Focus mode crashes every list request (`TypeError`) | `backend/iam/models.py:1528` |
| 2 | 🔴 High | `is_object_accessible` treats non-recursive assignments as recursive → read privilege escalation | `backend/iam/models.py:1332-1359` |
| 3 | 🟠 Medium | IdP-group role grants ignore the `idp_groups` feature flag | `backend/iam/models.py:1227` |
| 4 | 🟠 Medium | `descendants` closure serialized in every Folder API response | `backend/core/serializers.py:2285` |
| 5 | 🟡 Low | `is_access_allowed` lost its `is_authenticated` guard | `backend/iam/models.py:1263` |
| 6 | 🟡 Low | `get_iam_folder_id` raises `AttributeError` on null scope FK | `backend/iam/models.py:1665` |
| 7 | 🟡 Low | Codename reconstruction silently downgrades custom permissions | `backend/iam/models.py:1276` |

---

## 1. 🔴 Focus mode crashes every list request

**Location:** `backend/iam/models.py:1528`

```python
if base_folder is None or (focused_folder not in base_folder.ancestors):
```

`base_folder.ancestors` is a related **manager**. Managers define neither `__contains__` nor `__iter__`, so the `in` test raises `TypeError`. Since `get_accessible_object_ids` always passes `base_folder`, **any list endpoint 500s as soon as the user activates focus mode**.

**Fix:**

```python
if base_folder is None or not base_folder.ancestors.filter(id=focused_folder.id).exists():
```

The intended semantics ("keep `base_folder` only if it is a descendant of `focused_folder`") are otherwise correct.

---

## 2. 🔴 Non-recursive assignments grant recursive read access

**Location:** `backend/iam/models.py:1332-1359` (`is_object_accessible`)

The single-object path merges the perimeter folders of **all** assignments (flat and recursive alike) into one set, then tests it against the object folder's **full ancestor chain**:

```python
direct_accessible_folder_id_set = set(
    user_role_assignments.values_list("perimeter_folders__id", flat=True)
)
folder_chain_queryset = iam_folder.ancestors.all().union(folder_queryset)
is_accessible = bool(direct_accessible_folder_id_set & folder_chain_id_set)
```

A **non-recursive** assignment on a parent folder therefore matches objects in descendant folders — exactly what `is_recursive=False` must forbid. The list path (`get_allowed_folder_ids`) keeps the flat/recursive split correctly, so **list and retrieve disagree**.

**Failure scenario:** a role grants `view_appliedcontrol` on domain `F` with "sub folders are visible" unchecked. An `AppliedControl` lives in child folder `G`.
- List: correctly excluded.
- Retrieve (`GET /applied-controls/{id}` → `is_object_readable`): `F ∈ ancestors(G)` → intersection non-empty → **granted**.

Also reachable through the other `is_object_readable` gates (library, metrology, CRQ, chat/questionnaires).

**Fix:** delegate to the list-path algebra instead of re-deriving it:

```python
iam_folder_id = RoleAssignment.get_iam_folder_id(obj)
allowed = RoleAssignment.get_allowed_folder_ids(user, perm_prefix, model)
if Folder.objects.filter(id=iam_folder_id, id__in=allowed).exists():
    return True
# view-only published overlay, computed from the *expanded* allowed set
```

This single change also resolves two secondary divergences:

- **2a.** The published-object ancestor set is computed from raw perimeter folders in the retrieve path but from the recursively-expanded set in the list path → published objects visible in tables could 403 on open (under-permission, but user-visible inconsistency).
- **2b.** The published overlay in `is_object_accessible` applies to **any** perm, while the list path gates it to `view` only. Harmless today (all callers use `is_object_readable`), but the first `is_object_accessible(user, "change", …)` call would inherit published read-visibility on a write check.

And it deletes ~30 lines: the hand-rolled chain logic, a redundant `Folder.objects.get`, and a wasted perimeter query on the `FilteringLabel` branch.

---

## 3. 🟠 IdP-group grants ignore the feature flag

**Location:** `backend/iam/models.py:1227` (`get_role_assignments_from_user`)

```python
| Q(user_group__in=UserGroup.objects.filter(idp_groups__in=user.idp_groups.all()))
```

This branch is unconditional. The groups cache it replaces gates the same expansion behind `ff_is_enabled("idp_groups")` — explicitly so that **disabling the flag immediately revokes inherited roles** (`backend/iam/cache_builders.py:295-300`). `User.is_admin()` still honors the flag; the queryset path no longer does.

**Fix:** apply the IdP branch only when `ff_is_enabled("idp_groups")`.

---

## 4. 🟠 `descendants` leaks through the Folder read serializer

**Location:** `backend/core/serializers.py:2285` (`FolderReadSerializer`, `fields = "__all__"`)

`fields = "__all__"` now includes the new closure M2M: every folder response ships its full descendant UUID list — for the root folder, that is **every folder in the organization**. Consequences: payload bloat on the folders table, and folder-ID enumeration through published ancestor folders readable from below.

**Fix:** exclude `descendants` from `FolderReadSerializer` (the write serializer already excludes it), and audit any other serializer over `Folder` that uses `__all__` (import/export, data wizard).

---

## 5–7. Hardening (cheap, recommended)

- **5.** `is_access_allowed` no longer checks `is_authenticated`; an anonymous user with the `view_permission` perm short-circuits to `True` (`backend/iam/models.py:1276`). The global `IsAuthenticated` DRF default makes this unexploitable today — restore the guard anyway so the function's contract doesn't depend on middleware configuration.
- **6.** `get_iam_folder_id`: a nullable scope FK (e.g. a derived-scope object with its relation unset) raises `AttributeError` instead of the intended `ValueError`. Guard the `None` case.
- **7.** `is_access_allowed` derives `perm_type = perm.codename.split("_")[0]` and reconstructs `{prefix}_{model}`. Round-trips correctly for today's overrides (`approve_riskacceptance`, `transition_requirementassignment`) but silently downgrades any codename whose model part differs from `model.__name__.lower()` (e.g. `view_compliance_assessment_full` → checked as plain `view_complianceassessment`). Since the function already holds the `Permission` object, filter directly: `role__permissions=perm`. Implement by extracting the folder-expansion logic of `get_allowed_folder_ids` into a helper taking an assignments queryset, shared by both entry points.

---

## Simplifications (in scope: the PR owns these lines)

| Item | Location | Effect |
|------|----------|--------|
| Root fast-path: treat `base_folder = root` (no focus var) as `None` | `get_allowed_folder_ids` | Standard list path skips the focus machinery and its **3 eager `.exists()` queries per request**; members of the triplet become fully lazy |
| Hoist `get_iam_folder_field(model)` out of the view/change/delete loop | `backend/iam/models.py:1719` | Cosmetic; introspection computed once instead of 3× |
| Fetch only `parent_folder_id` in `_update_descendants_on_parent_folder_change` | `backend/iam/models.py:212` | Removes a full-instance `SELECT` on **every** `Folder.save()` |
| Batch `_update_descendants_at_creation` per-ancestor `.add()` loop into one `bulk_create` | `backend/iam/models.py:200` | One query instead of one per ancestor (minor; creates are rare) |
| Rename prefix parameters `perm` → `perm_prefix` (reserve `perm` for `Permission` instances) | `get_allowed_folder_ids`, `get_role_assignments_from_permission`, `is_object_accessible`, actor/label helpers | Two different argument kinds stop sharing one name; free now, breaking after release |

**Perf note (accepted trade-off):** `is_access_allowed` now costs several queries per call and appears in loops (e.g. bulk update/delete, `backend/core/views.py:1353`). Acceptable for this PR; revisit if hot paths show up in profiling.

---

## Tests to add

| Test | Pins |
|------|------|
| Non-recursive assignment: retrieve agrees with list (object in child folder denied on both) | Finding 2 |
| Published object outside granted scope: retrieve/list parity | Finding 2a |
| List request with focus mode active | Finding 1 |
| `idp_groups` flag off → IdP-inherited access revoked | Finding 3 |
| Folder API response contains no `descendants` field | Finding 4 |
| Closure integrity after create / reparent / delete (compare against `parent_folder` walk) | Migration + save hooks |
| Reparent a folder under its own descendant is rejected | Cycle guard (verify one exists; if not, that's a bug) |

---

## Explicitly out of scope (follow-up phases)

Kept out to keep this security-sensitive diff reviewable:

1. **Conformance matrix suite** — {flat, recursive} × {folder relation} × {published} × {focus} × {principal type} × {model kind}, asserting list/retrieve/write agreement.
2. **Internal consolidation** — route all verbs through one algebra, one model→folder contract, special-model dispatch; introduce the single-perm `get_accessible_ids(user, perm_prefix, model)`, with `get_accessible_object_ids` temporarily wrapped over it.
3. **Call-site migration** — internal callers move from triplet unpacking to the single-perm verb (mechanical); `get_accessible_object_ids` is then removed.
4. **IAM snapshot-cache removal** (~−800 lines) — the closure becomes the single derived structure.
5. **Publication rules per (domain, object type)** — replaces per-object `is_published`; removes the last row-level predicate from the decision layer.

**Estimated effort for this report's items:** ~1 day including tests; net negative diff on `iam/models.py`.
