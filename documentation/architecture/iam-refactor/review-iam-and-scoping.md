# IAM & scoping — target specification for object visibility

- **Status:** **frozen — implementation baseline** (approved by external review, 2026-08-23)
- **Date:** 2026-08-23 (rev. 3.4 — virtual membership evaluation and its hardening, after four external review rounds; rev. 3.3 carried the architectural approval and precision edits: principal invariant, homogeneity assertion, operator gate, semantic role contract, published aggregates)
- **Origin:** design review of `feat/move_is_published_field_to_folder`, extended into a full redesign discussion (@eric-intuitem + Claude), hardened across four external review rounds.
- **Supersedes:** `documentation/architecture/decisions/is-published-field-removal.md`; rev. 1 (overlay + modes + markers); rev. 2 (kinds + per-object flag); rev. 3 (seeded-everywhere); rev. 3.1's member-group lifecycle and migration staging.
- **Complements:** `documentation/architecture/iam-refactor/iam-target-architecture-plan.md` (Phases 0–4 unchanged; this document replaces Phase 5).

---

## 1. Problem statement

CISO Assistant has a valuable concept: some objects are visible from sub-domains without needing a role assignment there. Catalogs, shared vocabularies, and policies would be unusable without it. **We keep this concept.**

Its implementation — the `is_published` boolean — failed, for four reasons:

1. It existed on **158 models**, including ones where publication is meaningless (components, entitlements, settings) and ones where it must never be off (frameworks, labels).
2. Its default varied by model and by era, and **seventeen different pieces of code** set it: importers, save hooks, settings viewsets, denormalization chains. Nobody could list them.
3. It was **never exposed in the UI**, so users could not operate it — only code did, inconsistently. (Its near-zero deliberate usage in the fleet is therefore *not* evidence about demand, and is not used as an argument in this document.)
4. Some access paths ignored it entirely: the actor pickers and the users list gave different answers about the same person.

**This specification introduces no new authorization decision primitive: ambient visibility becomes ordinary RBAC data — derived member groups plus removable role assignments, surfaced as one folder toggle and two assignment controls. The resolver contains zero visibility-specific rules, and RoleAssignment gains no lifecycle state. In one line: principal group + semantically-defined role + folder scope.**

## 2. Foundations that do not change

This specification changes object visibility only. Everything below stays exactly as it is today:

1. **The RBAC data model.** Folders form the organization tree. A Role is a set of per-model CRUD permissions. A RoleAssignment gives a user group a role over a set of folders, optionally including all their sub-folders (`is_recursive`). Role assignments for humans are held by **groups only**, and the allowed principals are exactly two kinds (boot-checked): **role×domain generated groups**, and **derived member groups** (§4.1). Member-group *derivation sources* are the generated groups only — derived groups may be principals, never sources. **Effective membership of a UserGroup** is one defined relation: direct membership ∪ (when the `idp_groups` feature is enabled) membership via a mapped IdP group — and it is consumed by **both** principal resolution and the member-group evaluator, so a SCIM-provisioned user who holds a generated group's assignments only through the IdP mapping is a member wherever a directly-added user would be. The schema's direct-user assignment path (`Q(user=user)`) is reserved for service accounts; the boot check rejects it for humans, and **zero human direct-user assignments is a release/upgrade precondition**: if the fleet or self-hosted scan finds any, the upgrade halts with a report and requires remediation — they are never silently converted to broader generated groups. Service accounts have their own separate assignment path.
2. **The single decision primitive.** Every access question is answered by `is_access_allowed(permission, folder)`, or by its bulk form. A permission check always names a folder; instance-wide operations use the root folder.
3. **Enforcement points stay where they are.** Lists are filtered in `get_queryset`, creation is checked in serializers, single-object access in `RBACPermissions`.
4. **Managed IAM groups.** The platform already generates per-folder managed groups derived from available roles, governed by the `create_iam_groups` toggle. This specification adds one derived group kind per folder whose **existence is provisioned** by the same machinery under its own toggle (§4.1) and whose **membership is evaluated virtually** in the engine — never stored.

## 3. The mental model (documentation only — never code vocabulary)

The org tree is a **building**: Global is the building, domains are floors, sub-domains are rooms. Role assignments are **badges**; a role is a **badge profile** — which drawer types (models) a badge opens, with which gestures (view / add / change / delete). Content lives in typed **drawers**.

A floor's **members list** — everyone working on that floor or below — exists when the floor's manager **switches it on**. With the list in hand, two things become possible: giving the floor's members a **default profile** on the floor itself, and naming the floor's members as the **audience of another space** (a shared room, a shelf). Switching the list off destroys it — after showing the manager everything that depends on it.

A fresh building ships with one decision already made: the building's list is on, and its members carry the `Catalog Reader` and `Directory Reader` profiles — the library, the vocabulary, the staff directory. That default is a **dial, not a law**: any floor's default profiles can be changed, up to full `Reader` (radical transparency) or down to nothing.

Nothing else is automatic. **Visitors** (third parties) are on no members list, ever. **Street-entrance meeting rooms** (enclaves) don't put anyone on a floor's list. Sharing is always handing a profile to a named list — never a property of the object, and never a side effect of delivering content.

| Analogy | Real term |
|---|---|
| Building / floor / room | Global folder / domain / sub-domain |
| Badge, badge profile | RoleAssignment, Role |
| Badge touch on a drawer | `is_access_allowed(perm, folder)` |
| Switching a floor's members list on | The folder's "create member group" toggle |
| Floor members list | `<domain> - members` managed group |
| Default profile for a floor's members | The folder's "default role(s)" control (projection of assignment rows) |
| Naming a floor's members as another space's audience | The folder's "shared with" control (projection of assignment rows) |
| Visitor | Third-party principal |
| Street-entrance meeting room | Enclave folder |

The analogy is explanatory only. Code and API keep the real names.

## 4. The model (normative)

There is **no ambient-visibility mechanism**. Visibility is `is_access_allowed(view_M, folder)` — nothing else, for anyone, ever. What used to be "publication" is expressed entirely as data:

### 4.1 The member groups

**Lifecycle — an explicit toggle.** Each folder has a **"create member group"** provisioning toggle (a stored folder field, like `create_iam_groups`; provisioning state, not visibility policy — no visibility semantics are ever stored on Folder). Switching it **on** creates `<F> - members`, carrying an **immutable structural discriminator** — a protected managed-group kind (`DOMAIN_MEMBERS`) set at creation and never editable. **The engine keys its special behavior on this kind, never on names or codename prefixes** (`BI-UG-MBR` is a naming convention, not a semantic). **The group's lifecycle and folder binding are equally protected**: `DOMAIN_MEMBERS` groups may be created or deleted only through the folder toggle, and their associated folder can never be reassigned. Switching it **off** destroys the group **and every assignment referencing it** — the folder's own default roles and any other folder's shared-with rows — after an **impact preview** enumerating exactly what will be removed, and with an **audit event** listing it. The admin is always free to reset the toggle; the system's job is to make the blast radius visible, not to forbid it. The cascade additionally stores a **restorable manifest** of the removed assignments, so re-enabling the toggle can offer to recreate them. **Invariant, checked both ways: the members group exists iff the toggle is on; no assignment ever dangles.**

**Derivation (explicit source set).** `<F> - members` = the **active** internal human users with **effective membership** (§2.1: direct ∪ IdP-mapped, flag-gated) in the **role×domain generated groups** of `F` or of any non-enclave descendant of `F`. Excluded from the source set: derived member groups themselves (no circular derivation — derived groups may be assignment *principals*, never derivation *sources*), third-party principals (`User.is_third_party`), service accounts, and deactivated accounts (`is_active=False`). **Enclave exclusion is defined by path**: a generated group contributes members only if **the path from its folder up to the audience folder crosses no enclave boundary** — sufficient even when ordinary folders exist beneath an enclave (nested configurations are tested, not just direct enclave moves). A boot check enforces that every human role-assignment principal is one of the two allowed kinds (§2.1), which is what makes this derivation complete; if a legitimate exception ever appears, the check fails loudly and this definition is revisited. **An enabled member group may legitimately have zero effective members** (an empty branch) — this is a valid state, not an anomaly.

**Evaluation — virtual, in the IAM engine (no materialization, no synchronization).** The members group is a real `UserGroup` row (assignment principal, picker entry, register identity) that stores **no membership**. Membership is computed at evaluation time inside principal resolution, with one closure join: *user's generated groups → their folders → non-enclave ancestors via the `descendants` closure → member groups (toggle on) of those ancestors* — with the `is_active` / `is_third_party` / service-account exclusions as query filters. No independently materialized member-group state can become stale; evaluation reflects the current committed source memberships and folder closure — deactivations, group changes, and folder moves take effect on the first evaluation after the source transaction commits, because nothing is copied (the closure update the platform already performs *is* the membership update). One canonical helper (`is_member(user, folder)` / `members_of(folder)`) serves the engine, the UI's live member list, and any future feature — **and it is the only door**: no authorization path may join the raw group-membership table for member groups; interactive checks, bulk folder resolution, RAG filtering, exports, and background jobs all use this abstraction (invariant, grep-able). **Caching — resolved, not optional**: the initial implementation does **not** cache expanded membership. Caching may be introduced later only with documented revocation consistency, invalidation rules, and failure behavior — authorization caching is never an unspecified implementation choice. Query-plan tests cover deep trees, users with many generated groups, and duplicate paths, with **deduplication mandatory**. **The staleness claim is qualified honestly**: virtual evaluation eliminates member-group staleness as a category, but correctness now rests on the folder `descendants` closure — the existing `check_iam_closure` integrity command remains mandatory and is explicitly load-bearing for membership. This is stated honestly: it is **one derived-principal expansion rule in group resolution** — principal semantics, not visibility semantics; the visibility layer keeps zero special rules. Folder moves still emit the **audit event** and **access-impact preview** (§4.1 toggle treatment applies to folder deletion retiring references).

**Integrity (mostly dissolved by virtual evaluation).** With no materialized state, there is nothing to synchronize, reconcile, or quarantine: no independently materialized member-group state can become stale. What remains: a **property test** in CI asserting the virtual expansion ≡ an independent reference recompute (guarding the query itself), and correctness tests covering moves into and out of enclave branches, deactivation taking effect on the next evaluation, and multi-path membership. The rev-3.2 production-integrity apparatus (live reconciliation, health flags, fail-closed quarantine, transactional membership walks) is retired unbuilt — it was the cost of materialization, and the cost is gone with it.

### 4.2 The two folder controls and their assignments

Both controls are **projections, never columns**: what is stored is the assignment rows themselves; the folder form reads and writes them, and the role-assignments register shows the same rows. One source of truth, two views. Both require **IAM-administration rights** on the folder (the permission that governs role assignments there, not mere `change_folder`). Both are new IAM UI surfaces, and this document says so plainly.

1. **"Default role(s)"** — available once the folder's member group exists: the role(s) `<F> - members` holds **on `F`**. Set-valued, usually a singleton. Each entry is one row: `<F> - members × role × {F}`.
2. **"Shared with"** — the audience editor: rows of *(another folder's member group, role)* granting **on this folder**: `<other> - members × role × {this folder}`. Only **existing** member groups are selectable — if the audience folder's toggle is off, the admin enables it there first. Two explicit acts, no virtual materialization anywhere.

All resulting assignments are **ordinary, admin-owned, removable rows** — not builtin-protected, never re-created behind an admin's back — and **non-recursive**, which is load-bearing: a recursive one would expose descendant-folder content within the branch (a sensitive library loaded into a sub-folder would become readable by the whole branch), defeating placement-scoping.

**Fresh installs ship one decision, two rows** (and Global's member-group toggle on):

| Assignment | Role |
|---|---|
| `Global - members × Catalog Reader × {Global}` | **Catalog Reader** (`BI-RL-CAT`): view on all *definition* models — frameworks, matrices, threats, reference controls, terminologies, labels, asset classes, classification schemes (and levels), custom-field definitions, mapping sets, TTPs, document templates. |
| `Global - members × Directory Reader × {Global}` | **Directory Reader** (`BI-RL-DIR`): view on **User, Team, Entity** (and therefore Actor, by delegation). |

**Directory reads are safe for everyone, by design, with no role provenance**: the resolver returns booleans, not which role granted them, so **all normal User reads expose the safe projection** (picker fields only); administrative metadata — MFA, IdP state, admin flags — is served exclusively by a separate administrative endpoint under its own permission. `Directory Reader` grants plain `view_user`/`view_team`/`view_entity` with no serializer conditionality anywhere. (This is also a hardening independent of this specification.)

Replacing a default role with **Reader** is radical transparency; any custom role sets any posture between. Below Global, fresh installs set nothing; every further toggle and role is an administrator's decision. **Operator and user documentation describes `Global - members` as "all assigned internal members"** — never "all accounts" — because users in no generated group intentionally remain excluded.

**Built-in roles are semantically defined and tenant-immutable.** `Catalog Reader` *means* "may read catalog objects"; its permission list is the current answer to that semantic, not its identity. It evolves with the product under exactly two rules: **(i)** a new model classified as catalog adds its view permission in the same release — no existing rows are exposed, but existing assignments **prospectively authorize all future rows** of the new model; this is legitimate precisely because it follows the semantic contract, and it is stated here so nobody discovers it by surprise. A CI rule requires **every new securable model to be classified** — Catalog, Directory, Operational, or explicitly unclassified — so the decision is never made by omission. **(ii)** Reclassifying an *existing* model into a built-in role is an **access migration** — measured, reviewed, and release-noted with the same discipline as the seeding gates, because it exposes existing data. There is no role versioning: one role, one meaning, fleet-wide. **Custom copies do not follow**: a custom role copied from `Catalog Reader` is a static permission set and will not acquire future catalog models; upgrade reporting identifies custom roles containing catalog/directory/operational permissions so administrators can decide whether to extend them. Tenants never edit built-in roles (`Catalog Reader`, `Directory Reader`, `Operational Reader` — `BI-RL-OPR`: Asset, AppliedControl and its Policy proxy, Evidence, SecurityException, Vulnerability, Incident; documents and assessments deliberately excluded — and `Reader`); customization means replacing an assignment's role with a custom copy.

### 4.3 Invariants (each is a conformance test)

1. **No per-object visibility state exists anywhere** — no flag, no column, no property.
2. **No visibility-specific code exists in the resolver.** `readable(u, M)` ≡ `get_allowed_folder_ids(u, view_M)`; the target plan's overlay seam closes empty.
3. **RoleAssignment has no lifecycle state.** No enabled/status field; migration proposals live outside IAM until accepted (§6). (Quarantine no longer exists as a concept — there is no materialized membership to quarantine.)
4. **Human role-assignment principals are exactly the two allowed kinds** — generated role×domain groups, and derived member groups (boot check); derived member groups never appear in their own derivation source.
5. **Members groups are derived-only** (no UI/API mutates membership); existence obeys the toggle invariant (§4.1), checked both directions, with no dangling references.
6. **Identity gates ambience**: third parties, enclave-scoped users, service accounts, and deactivated accounts are never members. A service account gets explicit grants at creation, both offered default-checked: `Catalog Reader` on Global (integrations reading frameworks fail without it) and `Directory Reader` on Global (integrations resolving users/owners fail without it — on main, service accounts saw users via the published mechanism). Work access remains its scoped roles, via the direct-assignment path reserved for machines (#53; exempt from row 27).
7. **Content flows never create or modify IAM.** Loading a library or authoring definitions places content only (a passive informational note is permitted). Lifecycle features (publishing a document, issuing a finding) act **by placement** — putting the published revision where its audience already reads — never by writing grants. Any future workflow that must create an assignment requires the IAM-administration permission explicitly; content-edit permission never implies it.
8. **Components follow their aggregate root; delegates follow their delegatees** (Actor ≡ readable User ∪ Team ∪ Entity — §7.1).
9. **Role permission lists are the taxonomy.** Built-in role semantics are fleet-consistent; their permission lists are product-managed and may change only under the role-evolution rules (§4.2).

### 4.4 What was considered and rejected (for the archive)

- **Per-object flags** (`is_published`, rev. 2's `visible_to_descendants`): replaced by placement, default roles, and shared-with audiences. Evidence-gated reintroduction on one model stays possible.
- **The resolver overlay with per-model conditioning ("the amplifier")**: the last non-RBAC rule; traded for pure data (decision #26). Its least-privilege function survives as expressible policy and as the migration equivalence gate (§6).
- **Member-group lifecycles, three rejected variants**: reference-counted implicit existence (materialize/GC machinery, virtual pickers); `create_iam_groups`-tied lifetime (couples two unrelated provisioning concerns); default-role-bound existence (rev. 3.1 — broken by the shelf pattern: audiences are cross-folder, so existence cannot depend on the folder's own defaults). The dedicated toggle (#34) supersedes all three.
- **Blocking toggle-off while the group is referenced**: rejected as inconsistent — for a derived group, "non-empty" is not admin-actionable; instead, toggle-off cascades with preview and audit.
- **An "all active internal accounts" group**: would resurrect the unconditional lobby; a user in no managed group sees nothing, by design.
- **Role-provenance-dependent serializers** ("safe fields if access came via Directory Reader"): unimplementable in the primitive — the resolver returns booleans, not provenance; superseded by the universal safe projection (§4.2).
- **Per-model mode enums, folder visibility flags, board-subdomains, twin `view_published_*` permissions, a global "everyone" principal, paradigm flags with legacy markers**: see the decision log.

## 5. Sharing patterns (how every use case is expressed)

1. **Org-wide catalog**: ships working — Global's default roles.
2. **Sensitive/domain catalog** *(follow-up feature — today `LibraryImporter` loads into Global only)*: load the library into the domain; then enable the domain's member group (if not already) and set its default role (`Catalog Reader`, or narrower). The load itself never grants anything. Until the feature ships, all libraries are Global and covered by the Global defaults; the pattern applies today to domain-authored definitions (labels, asset classes, classification schemes, custom fields).
3. **Cross-domain operational composition**: `Operational Reader` among a folder's default roles, where wanted (and where migration proves it equivalent, §6).
4. **The shelf pattern** (per-object sharing at folder granularity): create a sub-folder (`EMEA/Shared`), move the objects in, then on the shelf's **"shared with"** control add *(EMEA - members, reader role)* — producing `EMEA - members × role × {EMEA/Shared}`. If EMEA's member group doesn't exist yet, enable EMEA's toggle first. Since assignments are non-recursive, **a shelf never inherits its parent's default; it always carries its own row.**
5. **Publishing a document / issuing a finding**: the lifecycle act creates an **independent, immutable published aggregate** — a snapshot object that is its own aggregate root (the published revision with its manifest/hash, per the findings roadmap) — and **places that aggregate** where its audience already reads (a shelf, the enclave, the portal). The working container and its revisions stay home, so the components-follow-root invariant is never bent: nothing that is a component ever changes folder on its own. Placement, not grants; *publish* stays a product verb; IAM never moves underneath it.
6. **"Publish a risk analysis as a template"**: derive a frozen definition-kind copy (snapshot / library-builder path), place it; `Catalog Reader` does the rest.
7. **Audience-scoped sharing**: a shared-with row naming that audience's member group.
8. **Custom-field definitions and form rendering**: rendering-critical schema is UI configuration, not data. Form rendering consumes a **restricted form-schema projection** (name, type, choices) available to anyone who can view or edit the host object — independent of catalog grants — so configured fields are **never silently absent** from forms. Full `CustomFieldDefinition` objects (administration) remain RBAC'd like everything else.

## 6. Migration & transition

The migration must preserve **both** dimensions of today's behavior, and they are different measurements:

- **Object visibility** (what content is exposed): preserved by the seeds below.
- **Principal capability** (who may see which kinds): on main, the published mechanism was conditioned per user (`view_M` held below); a default role is not. Seeding can therefore expand capability for principals whose roles lacked `view_M`. **Equivalence is proven per seed, exactly — never sampled, never assumed.**

1. **The full column drop survives unchanged** — all 158 `is_published` columns go; all seventeen implicit writers, the mixin, and the root force-publish hooks are deleted. **But the destructive step is gated (item 4): no tenant loses today's decision data before its continuity is settled.**
2. **Per-seed, exact gates.** Every candidate seed — Global `Catalog Reader`, Global `Directory Reader`, and each folder's `Catalog Reader` / `Operational Reader` — is evaluated independently:
   - **Content signal, per role**: `g(folder, role)` — does the folder hold content that main made visible downward *for that role's models*? (Operational content never justifies a `Catalog Reader` seed, nor vice versa.) No content, no seed.
   - **Capability signal, per seed**: `h(folder, role)` = the members of that folder's branch who would gain **at least one model permission** through that assignment. Computed **exhaustively** by set comparison of `old readable(user, model, folder)` (derivable while the flags still exist) versus `new readable(user, model, folder)` — an exact cohort query, not a sample.
3. **Seeding decisions**: a seed with `h(folder, role) = 0` is created enabled — equivalence proven, silence justified. A seed with `h > 0` becomes a **migration proposal stored outside IAM** (a proposal record, not a RoleAssignment) carrying the named principals and exactly which capabilities each would gain; it becomes an ordinary assignment only when an administrator accepts it. RoleAssignment itself never carries staged/disabled state (§4.3-3).
4. **Continuity for h > 0 tenants — nothing goes dark and nothing widens silently:**
   - **SaaS: an operator gate, technically guarded.** SaaS operators clear all tenant migration proposals *before* deploying the destructive release — this is fleet-deployment gating by operators, not application-level per-tenant release selection. As defense in depth, **the destructive migration itself refuses to run while unresolved proposals exist** for the tenant. The operator decision report and prepared rollback information are retained.
   - **Self-hosted: exact compatibility assignments, generated automatically.** For each affected branch, the migration creates view-only assignments reproducing each generated role group's *old* reach — grants only for the models the group's role already held, on the ancestor folders holding matching content. Verbose but exact, ordinary rows. The "migration compatibility" label is **not** an assignment field: the authoritative record is the migration's own metadata (which assignment ids it created), and the human-visible hint uses the assignment's existing name/description — non-authoritative provenance, never consulted by any decision. Consolidatable or deletable by the administrator later. No shadow mechanism survives, nothing goes dark, nobody gains.
   - **Homogeneity is a hard precondition of "exact".** Folder-level assignments can only reproduce folder-uniform visibility, so the migration asserts, for every migrated (folder, aggregate-root model) cohort: `count(distinct is_published) <= 1` — excluding the enumerated exceptional rows (hand-hidden, hand-published, documents), which follow their documented decisions. An unexpected mixed cohort **halts the destructive migration**, reports the objects, and requires placement remediation or explicit acceptance. The equivalence claim is accordingly qualified: *compatibility is exact for homogeneous publication cohorts; enumerated exceptions follow their documented migration decisions.*
   - **Zero human direct-user role assignments is likewise a hard precondition**: any found by the scan halt the upgrade with a report; remediation is manual, never a silent conversion.
   - **Existing service accounts get the same equivalence treatment** (creation defaults do nothing for accounts that already exist): before the columns drop, compute each service account's exhaustive old/new catalog **and** directory reach. **Exact compatibility assignments are the default outcome for every existing account.** Where the atomic built-in roles match the old reach exactly, they may be used as-is; where they would be **broader** (e.g. `Directory Reader` exposing Team/Entity to an account that held only `view_user`), SaaS may replace the compatibility assignments with the built-ins **only after explicit acceptance of the measured widening** through the operator proposal gate — **a rejected proposal leaves the exact compatibility assignments in place**. The guarantee: every account ends at exact equivalence or at an explicitly accepted, recorded delta — **no silent widening, no loss of existing machine access.**
5. **Seeded folders get their member-group toggle switched on by the migration** (that is data the admin can later switch off, cascade previewed like any other).
6. **Known, accepted deltas** (measured; single-object populations so far): policy documents published downward on main (documents are in no default role — remedy: shelf or lifecycle placement); hand-hidden operational objects becoming visible where seeds are enabled (mirror of the #4578 backfill precedent); hand-published records (issues, acceptances) going dark.
7. **No domain-loaded libraries exist at migration time** (loading is Global-only today), so domain-level definitions in the wild are the domain-authored kinds only.
8. **`SCHEMA_VERSION` bumps** in the same release; pre-upgrade backups are rejected cleanly instead of crashing mid-restore.
9. **UI shipped with this release**: the member-group toggle, the "default role(s)" and "shared with" controls (§4.2), and the access-impact previews on toggle-off and folder moves (§4.1). No other visibility UI exists.

## 7. Immediate fixes on main (independent of the rest)

### 7.1 Actor picker asymmetry (a confirmed bug)

Actors are the pointer records behind owner, reviewer, and assignee fields; each wraps a User, a Team, or an Entity. On main, the Users page and the actor pickers disagree: the Users list applies the general visibility rule, published mechanism included, while the actor path (`_get_actor_accessible_ids_by_perm`) checks role assignments only. Verified by test: a domain-scoped analyst sees a root-folder colleague on the Users page, but that same colleague is absent from the analyst's owner pickers.

The fix applies invariant 8: for the view prefix, the Actor delegate returns the actors whose underlying User, Team, or Entity is itself viewable by the general rule; the point check `_is_actor_accessible` delegates to `is_object_accessible` on the underlying object. Paradigm-proof: whatever the resolver returns tomorrow, actors follow.

### 7.2 GlobalSettings permission cleanup

Reads of UI configuration — feature flags, general settings, vulnerability SLA — become plain authenticated endpoints with no model permission. Every session needs them, so no role composition may be able to break them.

`view_globalsettings` and `change_globalsettings` are removed from the non-admin built-in roles. The permission returns to meaning "administers instance settings", checked as `is_access_allowed(perm, root)`. Sensitive rows (sso, infra-config, sec-intel-feeds) become admin-only through plain RBAC; the bolt-on `IsGlobalAdmin` guards stop being load-bearing, and the "sensitive settings MUST have extra checks" comment is deleted — the invariant moves from a comment into the permission model.

## 8. Impact on `feat/move_is_published_field_to_folder`

**Keep:** the full column-drop migrations (all models); serializer/UI/test cleanups; the migration-graph repairs (automation dependency `0003_workflow_engine`; restore the deleted metrology 0005 migration); the SSO `IsGlobalAdmin` guard (until 7.2 lands); the GlobalSettings attribute-name fix.

**Remove:** `ViewableFromDescendantsMode` and all per-model mode attributes; `Folder.viewable_from_descendants` (field, migration RunPython, root-folder invariant, FolderForm checkbox in CE and EE, content-types endpoint parameter, i18n keys); the `_viewable_from_descendants` property; the ancestor-visibility blocks in `iam/models.py` (both copies) and the published branch of `core/permissions.py`.

**Add:** the member-group toggle with cascade-with-preview (§4.1) and the **virtual membership evaluator** in principal resolution (§4.1, #49) with its expansion property test and query-performance tests; the `Catalog Reader` / `Directory Reader` / `Operational Reader` built-in roles (tenant-immutable, semantically defined, product-managed); the "default role(s)" and "shared with" folder controls with their permission gate; the boot checks (allowed principal kinds; toggle⇔group; no dangling references; group-kind discriminator immutability); the universal safe User projection + administrative endpoint split; the custom-field form-schema projection; scan signals `g(folder, role)` and `h(folder, role)`; the proposal store, exact-equivalence queries, pre-upgrade gate (SaaS) and compatibility-assignment generator (self-hosted); the service-account Catalog and Directory creation options, plus existing-service-account migration (§6); `SCHEMA_VERSION = 3`.

## 9. RAG / chat retrieval scope

1. Retrieval filters on `get_allowed_folder_ids(u, view_M)` — the same call every list view makes. Default-role and shared-with assignments carry the catalog into scope automatically; third parties and service accounts are scoped by their explicit grants.
2. Relevance stays a ranking concern (work folders vs catalog folders), never an access concern.
3. Entitlements and settings models are not indexed at all.
4. The critical test: every retrieved chunk's `(model, folder)` ∈ granted folders at query time.

## 10. Conformance matrix (collected)

1. `readable(u, M)` ≡ `get_allowed_folder_ids(u, view_M)` — no other visibility path exists (the overlay seam is empty).
2. No model carries visibility state (schema scan); RoleAssignment carries no lifecycle field.
3. Member-group existence ⇔ toggle on, both directions; no assignment references a missing group; the group stores no membership rows (schema test).
4. Toggle-off cascades: deletes the group, its default-role rows, and all shared-with rows referencing it — with an impact preview enumerating them and an audit event; nothing dangles afterward.
5. Clearing a folder's **default roles** deletes only those rows — shared-with assignments referencing its member group elsewhere are untouched.
6. Third-party, enclave-scoped, service-account, and deactivated principals ∉ any members group's evaluation; flipping `is_active` or `is_third_party` takes effect on the next evaluation, with no synchronization step.
7. Multi-path membership: a user reachable through several generated groups remains a member while any path exists — a property of the query, tested.
8. Human role-assignment principals are exactly the two allowed kinds — generated groups and derived member groups (boot check); derived member groups never appear in their own derivation source.
9. A user in no managed group sees nothing.
10. `readable(Actor)` ≡ actors backed by readable(User) ∪ readable(Team) ∪ readable(Entity) (7.1).
11. All normal User reads expose only the safe projection, for every caller; administrative metadata requires the administrative endpoint and permission (serializer contract test).
12. Default-role and shared-with edits change visibility for exactly the target folder (non-recursive), create/delete exactly the projected rows, and require the IAM-administration permission.
13. A shelf sub-folder never inherits its parent's default-role assignment (non-recursion test).
14. Folder move: the move and its closure update are **atomic**; membership is then reflected by the next evaluation with no membership-specific step; an audit event lists affected groups and assignments; cross-folder audience references are preserved (or explicitly retired on folder deletion, with preview and audit); enclave in/out moves **and nested-enclave configurations** covered.
15. Content flows and lifecycle features perform zero IAM writes (grep-able + integration test).
16. Custom-field form-schema projection: a host's form renders all applicable definitions for any user who can view the host, regardless of catalog grants.
17. Migration: per-seed exact equivalence — `h(folder, role) = 0` seeds produce identical `readable(user, model, folder)` before and after (exhaustive set comparison); `h > 0` candidates exist only as proposals outside IAM until accepted, and the destructive migration refuses to run while unresolved proposals exist; self-hosted compatibility assignments reproduce old reach exactly for homogeneous cohorts (no gain, no loss); the homogeneity assertion (`count(distinct is_published) <= 1` per migrated cohort, exceptional rows excluded) halts the migration on violation.
18. Built-in roles reject tenant edits (API write attempts rejected); only product migrations may alter their permission lists, and any alteration touching an existing model's permission is flagged as an access migration (test: built-in role diffs across an upgrade contain only new-in-this-release models, or carry an access-migration marker).
19. Toggle-off manifest restore: re-enabling the toggle and applying the manifest recreates exactly the removed assignments — same roles, same folders — against the recreated member group.
20. Virtual membership: the engine expansion ≡ an independent reference recompute (property test); deactivation, group changes, and folder moves are reflected on the next evaluation with no synchronization step; results are deduplicated; query plans are tested on deep trees and many-group users.
21. The member-group kind discriminator is immutable and is the sole trigger of special behavior (renaming a group changes nothing; setting the kind on an ordinary group is rejected); `DOMAIN_MEMBERS` groups are created/deleted only via the folder toggle, and their folder binding is never reassignable (API attempts rejected).
22. No code path joins the raw membership table for member groups — all consumers use the canonical expansion helper (static check + integration test).
23. Effective group membership (direct ∪ IdP-mapped) is one shared relation: a user reachable only via an IdP-group mapping appears in exactly the member groups a directly-added member of the same generated group would — tested with the `idp_groups` flag on and off. A feature-flag change affects **effective assignment reach** (RoleAssignment rows remain unchanged) and member groups in the same evaluation. **Union semantics are explicit**: a user reachable through both direct and IdP-mapped membership remains effective until the **last** path is removed — covered for direct removal, IdP mapping deletion, and feature-flag changes.
24. `check_iam_closure` is load-bearing for membership: a corrupted closure is detected by it, and the membership property test fails against a reference recompute that does not use the closure.
25. Every new securable model carries a classification — Catalog, Directory, Operational, or explicitly unclassified (CI check); an unclassified-by-omission model fails the build.
26. `makemigrations --check` clean; boot checks green.
27. Upgrade precondition: zero human direct-user role assignments — the destructive migration halts with a report if any exist; no silent conversion path exists.
28. Existing service accounts: per-account exhaustive old/new reach comparison; **exact compatibility assignments by default**; broader built-in roles only after an explicitly accepted and **recorded** widening (SaaS proposal gate) — a rejected proposal leaves the exact compatibility assignments in place. Conformance: post-migration reach is either **exactly equivalent** or carries an **explicitly accepted, recorded delta** — never silent widening, never access loss, for any machine principal.

## 11. Decision log

| # | Decision | Ruling |
|---|---|---|
| 1 | Concept of downward visibility for shared content | Keep — expressed as data, not mechanism. |
| 2 | Implicit per-object flags on 158 models, set by code | Removed. |
| 3 | Per-model mode enum / folder flag (the reviewed branch) | Rejected. |
| 4–5 | Full-visibility paradigm; bulk private-subdomain migration | Superseded / retired unbuilt. |
| 6 | Amplifier conditioning | Removed — traded for pure-RBAC expressiveness; resurfaces only as the migration equivalence gate (#33). |
| 7 | Global "everyone" principal | Superseded by `Global - members`. |
| 8 | `view_published_*` twin permissions | Rejected. |
| 9 | Hand-hidden / hand-published objects on main | Measured (fleet scan): artifact-dominated, single objects; deltas accepted and noted per tenant. |
| 10–15 | ClassificationLevel, mapping sets, Preset, export templates, DocumentTemplate, Tactic/TTP | Encoded in role permission lists: catalog content in `Catalog Reader`; Preset/LibraryDraft/export templates in no seeded role. |
| 16 | Records (acceptances, issues, metric instances) | In no seeded role; shared via shelves or shared-with rows. |
| 17 | GlobalSettings | Authenticated endpoints for benign reads; permission stripped from non-admin roles (§7.2). |
| 18 | Actor asymmetry | Current bug on main; fix first (§7.1). |
| 19 | Building analogy | Documentation only; never code vocabulary. |
| 20 | RAG scope | Granted folders — the only set there is. |
| 21 | Object-level visibility flag | Not built; every use case has a data expression (§5); evidence-gated reintroduction possible. |
| 22 | Operational objects | `Operational Reader` among default roles where wanted; migration-seeded only under the equivalence gates (#33/#41). |
| 23 | Finding / RiskScenario | Distribution belongs to the findings lifecycle — **by placement** (#36). |
| 24 | "Publish a risk analysis as a template" | Derive a frozen definition copy and place it. |
| 25 | Field naming (`visible_to_descendants`) | Moot — not built. |
| 26 | Member groups as the foundation | `<domain> - members`, derived; completeness enforced by the generated-group boot check (#44). |
| 27 | Root exception | Dead — Global is just the top folder whose toggle and default roles are set at install. |
| 28 | Migration continuity roles | Atomic `Catalog Reader` + `Operational Reader`, composed as default roles — subject to #33/#41. |
| 29 | The transparency dial | The folder's default role set — composed of atomic, immutable roles, administered as ordinary rows. |
| 30 | Fresh-install seeding | Global only: toggle on, `Catalog Reader` + `Directory Reader`. Below Global, nothing. |
| 31 | Content flows and IAM | Content flows never create or modify IAM; passive notes only. Extended by #36 to lifecycle features. |
| 32 | The folder controls | Projections of assignment rows — no stored visibility fields; honestly documented as new IAM UI surfaces, gated by IAM-administration permission. |
| 33 | Migration seeding policy (option A) | Equivalence-gated per seed; "nothing observable changes" withdrawn as a blanket claim. Refined by #41. |
| 34 | **Members-group lifecycle (final)** | An explicit **"create member group" toggle** per folder: on ⇒ group exists; off ⇒ group and every referencing assignment destroyed, after an impact preview and with an audit event. Supersedes reference-counted existence, `create_iam_groups`-tied lifetime, and default-role-bound existence (broken by the shelf pattern). A referenced-block on toggle-off was considered and rejected as not admin-actionable for a derived group. |
| 35 | Catalog / Directory split | `Directory Reader` (User, Team, Entity; Actor by delegation) separated from `Catalog Reader`. |
| 36 | Lifecycle features act by placement | Publishing / issuing places revisions where the audience already reads; zero lifecycle IAM writes. |
| 37 | Custom-field rendering | A restricted form-schema projection serves rendering independently of catalog grants; never silently absent. |
| 38 | Built-in roles: semantic identity, tenant-immutable | **Role versioning rejected as over-engineering** (user override of a review suggestion): a built-in role is defined by its semantic ("reader of catalog objects"), so new catalog models join it automatically (no existing rows exposed; existing assignments prospectively authorize future rows, per the semantic contract), while reclassifying an existing model is an access migration under the §6 discipline. One role, one meaning, fleet-wide; tenant customization = replacing an assignment's role with a custom copy. |
| 39 | Production integrity of derived membership | Superseded by #49: no independently materialized member-group state can become stale; the apparatus (reconciliation, health flags, quarantine, transactional walks) is retired unbuilt. A CI property test guards the expansion query. |
| 40 | **The "shared with" control** | The audience editor on each folder: rows of (another folder's member group × role) granting on this folder; only existing groups selectable; the shelf pattern's UI. |
| 41 | **Per-seed exact migration gates** | `g(folder, role)` content signals and `h(folder, role)` capability signals, per candidate seed including Global Catalog/Directory; equivalence by exhaustive set comparison; `h > 0` candidates are proposals outside IAM until accepted. |
| 42 | **h > 0 continuity strategy** | SaaS: pre-upgrade gate — the destructive release waits for the tenant's recorded decision. Self-hosted: auto-generated exact compatibility assignments (old reach reproduced; no gain, no loss; recorded in migration metadata, deletable). *(Adopted on recommendation — flag to revisit if the operational cost of the SaaS gate proves too high.)* |
| 43 | **Universal safe directory projection** | All normal User reads expose the safe projection for every caller (role provenance is unknowable in the primitive); administrative metadata behind a separate endpoint and permission. |
| 44 | **Derivation completeness enforcement** | Boot check: human role-assignment principals are exactly two kinds — generated role×domain groups and derived member groups; derivation *sources* are generated groups only; IdP-synced groups contribute via their mapping into generated groups. |
| 45 | **Homogeneity precondition** | The destructive migration asserts `count(distinct is_published) <= 1` per (folder, aggregate-root model) cohort (enumerated exceptions excluded); a mixed cohort halts it, reports, and requires remediation or explicit acceptance. "Exact compatibility" is claimed only for homogeneous cohorts. |
| 46 | **Published aggregates** | Publishing/issuing creates an independent, immutable published aggregate (snapshot + manifest, per the findings roadmap) placed at the audience location; working containers and their components never change folder on their own. |
| 47 | **Architectural approval** *(historical)* | Rev. 3.2 approved by external review subject to edits #44-46, the operator-gate clarification, and role versioning — the last later superseded by #38's semantic contract. |
| 48 | **Final approval (rev. 3.3)** | Approved for implementation planning. Final precision edits: "no new authorization decision primitive" wording; manifest-restore conformance row; operator vocabulary "all assigned internal members". Role versioning subsequently rejected — see #38. |
| 49 | **Virtual membership evaluation** | Member-group membership is computed in the IAM engine at evaluation time (one closure join in principal resolution) — no materialized rows, no synchronization; no independently materialized member-group state can become stale. Stated honestly as one derived-principal expansion rule in group resolution; visibility semantics remain zero-special. Supersedes #39's integrity apparatus. |
| 50 | **Implementation baseline** | Third review round's corrections incorporated: versioning leftovers purged (§8, invariant 9, #47 marked historical); prospective authorization of new-model access stated explicitly with a mandatory classification CI rule; custom-copy staticness documented with upgrade reporting; compatibility labeling defined as migration metadata + non-authoritative name/description. Approved as the implementation baseline. |
| 51 | **Virtual-evaluation hardening (4th review round)** | Stale materialization language purged (§2.4, §4.3-3, §8, conformance 14); structural `DOMAIN_MEMBERS` kind discriminator (never name-based); enclave exclusion defined by path with nested-enclave tests; the canonical expansion helper as the only door; staleness claim qualified — `check_iam_closure` explicitly load-bearing; caching/dedup/query-plan requirements normative. One new principal-membership primitive, no new authorization-decision primitive. |
| 52 | **Rev. 3.4 final precision** | Staleness wording made exact ("no independently materialized member-group state can become stale; evaluation reflects committed source memberships and closure"); effects land on the first evaluation after the source transaction commits; **no caching of expanded membership in the initial implementation** (later caching requires documented revocation consistency, invalidation, and failure behavior); `DOMAIN_MEMBERS` lifecycle and folder binding protected (toggle-only create/delete, folder never reassignable); #42 wording aligned to migration metadata. Approved to proceed: one dynamic principal-membership rule, one ordinary RBAC authorization rule, no content-specific visibility mechanism. |
| 53 | **SCIM / IdP-group completeness** | The IdP mapping grants assignments without direct group membership, so member-group derivation is defined over **effective membership** (direct ∪ IdP-mapped, flag-gated) — the same single relation principal resolution uses; SCIM-provisioned users are members wherever directly-added users would be. Human direct-user assignments remain forbidden (boot check), with a pre-ship scan count. Closes the residual of review blocker 6. |
| 54 | **Baseline frozen** | Approved and frozen as the implementation baseline (fourth-round reviewer sign-off). Architecture revision stops here; further work is implementation decomposition and threat-model/test cases, tracked outside this document. |
| 55 | **Post-freeze acceptance clarifications** *(no architecture change)* | Row 23 reworded to "effective assignment reach" (RoleAssignment rows unchanged by flag flips) with explicit union semantics incl. IdP-mapping deletion; zero human direct-user assignments promoted to a halting release/upgrade precondition (row 27) — never silently converted. Rev. 3.4 remains frozen. |
| 56 | **Service-account grants** *(no architecture change)* | Separate track confirmed: SAs never enter member groups; at creation, `Catalog Reader` **and** `Directory Reader` on Global are offered default-checked (directory needed for owner/user resolution — main's published users covered this); work access = scoped roles via the machine-reserved direct path. |
| 57 | **Existing-service-account migration** *(no architecture change)* | Creation defaults (#56) cover new accounts only. The migration computes each existing SA's exhaustive old/new reach; **exact compatibility assignments by default**; built-ins replace them only on explicit, recorded acceptance of the measured widening, with rejection leaving compatibility in place. Guarantee: exact equivalence or accepted recorded delta — no silent widening, no machine-access loss. Stale principle 4 and §8 wording fixed. |
| 58 | **Definitive sign-off** | Row 28's exact-vs-accepted contradiction resolved (compatibility-by-default, accepted-recorded-delta alternative, rejection fallback explicit in §6). External reviewer's definitive sign-off: no further design review needed. The baseline is final. |

## 12. Design principles distilled

1. **One primitive.** If a capability can be expressed as groups, roles, and assignments, it must be. The count of visibility-specific mechanisms in this design is zero, and RoleAssignment has no lifecycle states.
2. **Defaults are data; existence is a decision.** The member-group toggle, the default roles, and the shared-with audiences are all explicit, removable administration — with previews and audit where removal cascades.
3. **Invariants live in structure** — boot checks, integrity checkers, conformance tests — never in comments, save hooks, or conventions.
4. **Derived semantics must be independently verifiable**: property-test the virtual expansion against a reference recomputation, enforce closure integrity in production, and keep no separately synchronized membership state.
5. **Identity gates ambience**: third parties, enclave-scoped users, machine principals, and deactivated accounts get exactly their explicit grants.
6. **Components follow roots; delegates follow delegatees.**
7. **Placement scopes reference material; default roles and shared-with audiences share work; lifecycles act by placement; IAM is written only by administrators and the accepted parts of the install/upgrade seeding.**
8. **When an object seems to need special visibility treatment, first check whether a permission is doing double duty** (the GlobalSettings lesson).
9. **Capability-changing steps are measured exactly before they are claimed** — object fidelity and principal-capability equivalence are separate, exhaustive measurements, and destructive steps wait for continuity to be settled.
