# IAM grant resolution

How an access question is answered in `backend/iam/models.py`. Companion to the
ADR [Remove all `is_published` fields; visibility becomes a folder default role](decisions/is-published-field-removal.md),
which records why the model looks like this; this page records how the code is
wired so a change can be reviewed against the intended structure.

There are two grant sources:

- **stored role assignments** — `RoleAssignment` rows, recursive or not;
- **virtual assignments** — `Folder.default_role`, granted non-recursively to
  the folder's members (see the ADR for the audience rule), computed on read
  and never written anywhere.

And two kinds of question:

- **verdicts** — "may this user do X here?", point or bulk;
- **listings** — "which permissions does this principal hold, and where?".

The two sources are enumerated in **exactly one function**,
`_get_grant_sources`, which returns them as a pair of branches. Each question
axis is a projection of that pair, and the verdict axis then has exactly one
coverage rule. Everything else is plumbing.

## Call graph

```mermaid
flowchart TB
  classDef amb stroke:#B4550A,stroke-width:2px
  classDef meet fill:#0E7C86,color:#ffffff,stroke:#0E7C86
  classDef data stroke-dasharray:2 3

  subgraph CALLERS["callers outside the file"]
    RBAC["RBACPermissions<br/>(object requests)"]
    QS["BaseModelViewSet<br/>(list filtering)"]
    RAG["chat / RAG scoping"]
    GATES["data-wizard · integrations gates"]
    UP["user-permission endpoints"]
  end

  subgraph POINT["point checks — one object, one folder"]
    IOR["is_object_readable"]
    IOA["is_object_accessible"]
    IAA["is_access_allowed"]
  end

  subgraph BULK["bulk checks — lists and filters"]
    GVOI["get_viewable / changeable /<br/>deletable_object_ids"]
    GAI["_get_accessible_ids"]
    GAFI["get_allowed_folder_ids"]
  end

  subgraph PRED["the two predicates"]
    COVQ["_coverage_q"]
    SCOQ["_scope_q"]
  end

  subgraph ANSWERS["permission listings"]
    HPA["has_permission_anywhere"]
    GP["get_permissions"]
    GPPF["get_permissions_per_folder"]
  end

  subgraph PROJ["the two projections"]
    GFS["_get_grant_folder_set<br/>→ GrantFolderSet (flat id lists)"]
    EGR["_get_effective_grant_rows"]
  end

  GSRC["_get_grant_sources<br/>stored ∪ virtual grants"]:::meet

  subgraph EXPLICIT["the stored branch — explicit assignments"]
    RAU["get_role_assignments_from_user"]
  end

  subgraph AMBIENT["the virtual branch — ambient default roles"]
    DRF["_get_default_role_folder_ids<br/>(the audience rule)"]:::amb
  end

  subgraph SCOPE["object → folder resolution"]
    GIFI["get_iam_folder_id"]
    GIFF["get_iam_folder_field"]
  end

  RATBL[("RoleAssignment table")]:::data
  FDR[("Folder.default_role")]:::data
  CLO[("descendants closure")]:::data

  RBAC -.-> IOR
  RBAC -.-> IAA
  QS -.-> GVOI
  RAG -.-> GAFI
  GATES -.-> HPA
  UP -.-> GP
  UP -.-> GPPF

  IOR --> IOA
  IOA -- "governing folder" --> GIFI
  GIFI --> GIFF
  IOA -- "delegates verdict" --> IAA
  IAA --> GFS
  IAA -- "one folder" --> COVQ
  IAA -- "focus prologue" --> CLO

  GVOI --> GAI
  GAI -- "folder field per model" --> GIFF
  GAI --> GAFI
  GAFI --> GFS
  GAFI -- "all folders" --> COVQ
  GAFI -- "focus / base clamp" --> SCOQ
  GAFI -- "effective-base resolution" --> CLO

  COVQ -- "recursive grants expand ↓" --> CLO
  SCOQ -- "base subtree" --> CLO

  HPA -- "exists()" --> EGR
  GP --> EGR
  GPPF --> EGR
  GPPF -- "descendant expansion" --> CLO

  GFS -- "folder-id lists,<br/>split by recursion kind" --> GSRC
  EGR -- "folder × codename rows" --> GSRC

  GSRC -- "stored assignments" --> RAU
  GSRC -- "virtual assignments:<br/>the audience rule" --> DRF
  GSRC -- "role holds the permission?" --> FDR

  RAU -- "direct ∪ group ∪ IdP" --> RATBL

  DRF -- "builtin-group grants only" --> RAU
  DRF -- "perimeters, self ∪ ancestors" --> CLO
  DRF -- "non-null default_role" --> FDR

  linkStyle 30,31,33,34,35 stroke:#B4550A
```

The solid teal node is the single meeting point of the two grant sources;
orange edges are the virtual (default-role) branch; dashed arrows come from
outside the file. Special-case leaves (`_get_actor_accessible_ids`,
`_get_permission_accessible_ids`, and `_get_role_assignments_from_permission`,
which now serves only the `FilteringLabel` add special case) are listed in the
table rather than drawn.

## The four invariants

1. **One meeting point.** The grant sources are enumerated only inside
   `_get_grant_sources`; its two consumers are the projections
   `_get_grant_folder_set` (verdict axis: flat folder-id lists by recursion
   kind) and `_get_effective_grant_rows` (listing axis: folder × codename
   rows). No other function reads `Folder.default_role` or combines
   assignments with default roles — so verdicts and listings agree by
   construction. Django forbids filtering a union, so the permission filter is
   applied per branch *inside* the builder; consumers project and combine the
   branches, they never re-derive them.
2. **Virtual grants never cascade.** The verdict projection merges the
   default-role folders into `GrantFolderSet.non_recursive_grant_folder_ids`,
   never into the recursive bucket — non-recursion is a property of the data
   shape, not a check.
3. **One verdict rule.** `_coverage_q` states coverage once — a non-recursive
   grant names the folder, or a recursive grant names it or an ancestor — and
   is applied to one folder (`is_access_allowed`) or to all folders
   (`get_allowed_folder_ids`). Focus mode and `base_folder` narrow the bulk
   result with `_scope_q`; they never introduce a second coverage rule. The two
   predicates must stay in **chained** `.filter()` calls: both join the
   multi-valued `ancestors` relation, and a single call would force one
   ancestor row to satisfy both. `GrantFolderSet` carries materialized flat id
   lists, so no union or subquery ever reaches the verdict SQL (PostgreSQL
   parser-depth safety).
4. **Raw `RoleAssignment` queries are for write-capability or conservative
   fast paths only.** Any *view*-access answer computed from the table alone
   misses virtual grants; a raw query is acceptable only where a false negative
   falls through to an accurate primitive.

These invariants are executable: `backend/iam/tests/test_access_oracle.py`
checks the resolver against a brute-force plain-Python oracle over seeded
worlds (point ⟺ bulk ⟺ listings, focus and base-folder clamps included).
A refactor of this subsystem should leave that file untouched and green.

## Function reference

| Function | Contract | Calls |
|---|---|---|
| **Point checks** | | |
| `is_object_readable` | Alias: `is_object_accessible` with `view`. | `is_object_accessible` |
| `is_object_accessible` | Resolves the object to its governing folder (existence, `Actor` delegation, IAM scope), then delegates the verdict. | `get_iam_folder_id` · `is_access_allowed` |
| `is_access_allowed` | The point verdict. Owns the prologue — anonymous, `Permission` view-only, `FilteringLabel` add, the focus-mode gate (root exempt) — then evaluates coverage on the one folder. | `_get_grant_folder_set` · `_coverage_q` |
| **The two predicates** | | |
| `_coverage_q` | The coverage rule, stated once (invariant 3), over flat literal `IN` lists. | — |
| `_scope_q` | The clamp: folder is the base folder or a descendant. Combined with coverage via chained `.filter()` calls only. | — |
| **The meeting point** | | |
| `_get_grant_sources` | The single function where the two grant sources are enumerated, as a (stored assignments, virtual default-role folders) pair of branch querysets. Principal dispatch lives here (`User` → effective assignment set, `UserGroup` → its own assignments); the optional permission filter is applied per branch. | `get_role_assignments_from_user` · `_get_default_role_folder_ids` |
| **The two projections** | | |
| `_get_grant_folder_set` | Verdict projection: flat folder-id lists split by recursion kind; virtual folders join the non-recursive bucket (invariant 2). Materialized — the verdict path carries no querysets. | `_resolve_permission` · `_get_grant_sources` |
| `_get_effective_grant_rows` | Listing projection: one row per (folder, codename, name, is_recursive) a grant names, unexpanded; NULL-perimeter rows preserved for parity. The permission-filtered form is for existence checks, not projection. | `_get_grant_sources` |
| **The stored branch — explicit assignments** | | |
| `get_role_assignments_from_user` | Effective assignments: direct ∪ group-carried ∪ IdP-mapped; inactive users get none. | — |
| `_get_role_assignments_from_permission` | The user's assignments whose role holds the permission — now only the `FilteringLabel` add special case. | `get_role_assignments_from_user` · `_resolve_permission` |
| **The virtual branch — ambient default roles** | | |
| `_get_default_role_folder_ids` | The audience rule: builtin-group-carried grants → non-enclaved perimeters → self ∪ ancestors carrying a default role. The third-party backstop lives here; service accounts never reach it (their assignments carry no builtin group). | `get_role_assignments_from_user` |
| **Bulk checks** | | |
| `get_viewable/changeable/deletable_object_ids` | Per-model object ids the user may view/change/delete. | `_get_accessible_ids` |
| `_get_accessible_ids` | Objects whose governing folder is allowed; special-cases `Permission` (everyone views, nobody writes) and `Actor` (delegates to the wrapped User/Team/Entity). | `get_allowed_folder_ids` · `get_iam_folder_field` |
| `get_allowed_folder_ids` | The bulk verdict: coverage over all folders, clamped by `_scope_q` when focus mode or `base_folder` narrows the scope (the narrower of the two wins when nested; disjoint → empty). In focus mode a covered root stays reachable. | `_get_grant_folder_set` · `_coverage_q` · `_scope_q` |
| **Permission listings** | | |
| `has_permission_anywhere` | "Holds the codename on any folder" — an `exists()` on the filtered relation. | `_get_effective_grant_rows` |
| `get_permissions` | Codename map of everything the principal holds, virtual grants included. | `_get_effective_grant_rows` |
| `get_permissions_per_folder` | folder-id → codenames map; recursive rows expand to descendants through one bulk closure query. | `_get_effective_grant_rows` |
| **Object → folder scope** | | |
| `get_iam_folder_id` / `get_iam_folder_field` | Governing folder of an object: its `folder` field, or the field named by `IAM_SCOPE_FIELD` (undeclared models raise `IAMNotImplementedError`). | — |

Function names, not line numbers, anchor this page: lines drift with every
edit, the structure only changes when someone adds a grant source — which, per
invariant 1, must happen inside `_get_grant_sources` and nowhere else.
