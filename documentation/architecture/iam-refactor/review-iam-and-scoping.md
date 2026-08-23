# IAM & scoping — target specification for object visibility

- **Status:** **baseline — frozen at rev. 3.6, final.** The fifth external review round and its wording repairs are fully absorbed; the change-control rule is now in force with no further exceptions: changes are implementation issues, threat-model findings, or **new ADRs referencing this baseline — never edits to this document.**
- **Date:** 2026-08-23 (rev. 3.6)
- **Origin:** design review of `feat/move_is_published_field_to_folder`, extended into a full redesign discussion (@eric-intuitem + Claude), hardened across five external review rounds — the fifth verified against code.
- **Supersedes:** `documentation/architecture/decisions/is-published-field-removal.md`; rev. 1 (overlay + modes + markers); rev. 2 (kinds + per-object flag); rev. 3 (seeded-everywhere); rev. 3.1–3.4 lifecycle and migration stagings.
- **Complements:** `documentation/architecture/iam-refactor/iam-target-architecture-plan.md` (Phases 0–4 unchanged; this document replaces Phase 5 and **promotes one of its cross-cutting deliverables to a hard dependency** — see §4.1 on `check_iam_closure`).

---

## 1. Problem statement

CISO Assistant has a valuable concept: some objects are visible from sub-domains without needing a role assignment there. Catalogs, shared vocabularies, and policies would be unusable without it. **We keep this concept.**

Its implementation — the `is_published` boolean — failed, for four reasons:

1. It existed on **158 models**, including ones where publication is meaningless (components, entitlements, settings) and ones where it must never be off (frameworks, labels).
2. Its default varied by model and by era, and **seventeen different pieces of code** set it: importers, save hooks, settings viewsets, denormalization chains. Nobody could list them.
3. It was **never exposed in the UI**, so users could not operate it — only code did, inconsistently. (Its near-zero deliberate usage in the fleet is therefore *not* evidence about demand, and is not used as an argument in this document.)
4. Some access paths ignored it entirely: the actor pickers and the users list gave different answers about the same person.

**This specification introduces no new authorization decision primitive: ambient visibility becomes ordinary RBAC data — derived member groups plus removable role assignments, surfaced as one folder toggle and two assignment controls. The resolver contains zero visibility-specific rules, and RoleAssignment gains no lifecycle state. In one line: principal group + semantically-defined role + folder scope.**

## 2. Foundations — facts about `main` today

This section states only what is currently true; the constraints this specification *adds* live in §4 and §6.

1. **The RBAC data model.** Folders form the organization tree. A Role is a set of per-model CRUD permissions. A RoleAssignment binds a principal to a role over perimeter folders, optionally recursive. The schema supports **both** user-group principals and direct-user principals, and `RoleAssignmentWriteSerializer` exposes all fields — nothing today prevents creating a human direct-user assignment. (The two-kinds principal rule, its write-time validation, and the migration precondition are **new requirements** — §4.3, §6.)
2. **The single decision primitive.** Every access question is answered by `is_access_allowed(permission, folder)`, or by its bulk form. A permission check always names a folder; instance-wide operations use the root folder.
3. **Enforcement points.** Lists are filtered in `get_queryset`, creation is checked in serializers, single-object access in `RBACPermissions`.
4. **Managed IAM groups.** The platform generates per-folder role×domain groups from available roles, governed by the `create_iam_groups` toggle; IdP-synchronized groups map onto them; no built-in role carries `add_usergroup`, so tenants cannot create additional principal groups. Users are created in the root folder; a scheduled task deactivates users past their `expiry_date` (expiry manifests as `is_active=False`). The `descendants` closure table is maintained on folder changes.

## 3. The mental model (documentation only — never code vocabulary)

The org tree is a **building**: Global is the building, domains are floors, sub-domains are rooms. Role assignments are **badges**; a role is a **badge profile** — which drawer types (models) a badge opens, with which gestures (view / add / change / delete). Content lives in typed **drawers**.

A floor's **members list** — everyone working on that floor or below — exists when the floor's manager **switches it on**. With the list in hand, two things become possible: giving the floor's members a **default profile** on the floor itself, and naming the floor's members as the **audience of another space** (a shared room, a shelf). Switching the list off destroys it — after showing the manager everything that depends on it.

A fresh building ships with one decision already made: the building's list is on, and its members carry the `Catalog Reader` and `Directory Reader` profiles — the library, the vocabulary, and the **people directory**. Teams and third-party entities are not directory entries; they are ordinary drawers, visible where your badge reaches, shareable like any other content.

That default is a **dial, not a law**: any floor's default profiles can be changed, up to full `Reader` (radical transparency) or down to nothing. Nothing else is automatic. **Visitors** (third parties) are on no members list, ever. **Street-entrance meeting rooms** (enclaves) don't put anyone on a floor's list and keep no list of their own. Sharing is always handing a profile to a named list — never a property of the object, and never a side effect of delivering content.

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

There is **no ambient-visibility mechanism**. Visibility is `is_access_allowed(view_M, folder)` — nothing else, for anyone, ever. One companion fact is recognized rather than invented: **nested serialization is a visibility path** — content may ride an aggregate the caller can read (embedded components and related names), governed by the host object's check, in the spirit of components-follow-roots. Conformance row 1 therefore claims uniqueness of *folder-visibility decision paths*, not of every byte's route to a screen.

What used to be "publication" is expressed entirely as data:

### 4.1 The member groups

**Lifecycle — an explicit toggle.** Each folder has a **"create member group"** provisioning toggle (a stored folder field, like `create_iam_groups`; provisioning state, not visibility policy — no visibility semantics are ever stored on Folder). Switching it **on** creates `<F> - members`, carrying an **immutable structural discriminator** — a protected managed-group kind (`DOMAIN_MEMBERS`) set at creation and never editable. The engine keys its special behavior on this kind, never on names or codename prefixes. The group's lifecycle and folder binding are equally protected: `DOMAIN_MEMBERS` groups are created or deleted **only** through the toggle, and their folder is never reassignable. **Enclave folders may not enable the toggle** — enclaves receive explicit grants only; a member-audience for a visitor space contradicts its purpose. Switching the toggle **off** destroys the group **and every assignment referencing it** — the folder's own default roles and any other folder's shared-with rows — after an **impact preview** and with an **audit event**. The preview shows the actor the affected rows (folder and role): grants *to* this group are information about the audience its administrator governs; administrators of the affected folders learn of the change through the audit event and their own registers. The cascade stores a **restorable manifest**; restore matches by natural keys and, where a target folder has since been deleted, **skips and reports** (partial restore is legal and explicit). **Invariant, checked both ways: the members group exists iff the toggle is on; no assignment ever dangles.**

**Derivation (explicit source set).** **Effective membership of a UserGroup** is one defined relation: direct membership ∪ (when the `idp_groups` feature is enabled) membership via a mapped IdP group — consumed by **both** principal resolution and the member-group evaluator, so they can never disagree. `<F> - members` = the **active** internal human users with effective membership in the **role×domain generated groups** of `F` or of any descendant of `F` reachable without crossing an enclave boundary: **enclave exclusion is positional, by path** — a generated group contributes members only if the path from its folder up to the audience folder crosses no enclave boundary (sufficient even when ordinary folders exist beneath an enclave; nested configurations are tested). Excluded from the source set: derived member groups themselves (principals, never sources), third-party principals (`User.is_third_party`), service accounts, and deactivated accounts (`is_active=False`; account expiry manifests as deactivation via the scheduled task, so it takes effect within the task's cadence). **An enabled member group may legitimately have zero effective members.**

**Evaluation — virtual, in the IAM engine (no materialization, no synchronization).** The members group is a real `UserGroup` row (assignment principal, picker entry, register identity) that stores **no membership**. Membership is computed at evaluation time inside principal resolution, with one closure join: *user's effective generated groups → their folders → non-enclave-crossing ancestors via the `descendants` closure → member groups (toggle on) of those ancestors* — exclusions as query filters. No independently materialized member-group state can become stale; evaluation reflects the current committed source memberships and folder closure — changes take effect on the first evaluation after the source transaction commits. One canonical helper (`is_member(user, folder)` / `members_of(folder)`) serves the engine, the UI's live member list, and any future feature — **and it is the only door**: no authorization path may join the raw group-membership table for member groups; interactive checks, bulk folder resolution, RAG filtering, exports, and background jobs all use this abstraction. This is one **derived-principal expansion rule in group resolution** — principal semantics, not visibility semantics; the visibility layer keeps zero special rules.

**Performance budget (normative).** The expansion adds **at most one additional indexed query per principal resolution**, with the index plan covering the group kind, the folder toggle, and the closure through-table. `members_of(Global)` is an administrative UI operation: paginated, with an expected cost of one users×groups×closure sweep — acceptable for a page, never on a hot path. **Request-scoped memoization is permitted** (one resolution per request); the caching prohibition concerns **cross-request** state: the initial implementation does not cache expanded membership across requests, and later caching requires documented revocation consistency, invalidation rules, and failure behavior.

**Integrity.** With no materialized state, there is nothing to synchronize, reconcile, or quarantine. What remains: a **property test** in CI asserting the virtual expansion ≡ an independent reference recompute; correctness tests for enclave and nested-enclave configurations, deactivation, and multi-path membership. **Correctness rests on the folder closure**, so `manage.py check_iam_closure` — a cross-cutting deliverable of the companion plan (its §5), **not yet built** — is promoted to a hard dependency of this specification: it must exist before this ships (§8), run in CI and in the pre-flight (§6), detect-only with a separate repair mode; a detected corruption raises an operator alert and is repaired — the closure serves all folder-scoped access, so corruption there is a platform incident, not a member-group event.

### 4.2 The two folder controls and their assignments

Both controls are **projections, never columns**: what is stored is the assignment rows themselves; the folder form reads and writes them, and the role-assignments register shows the same rows. One source of truth, two views. Both require **IAM-administration rights** on the folder (the permission that governs role assignments there, not mere `change_folder`). Both are new IAM UI surfaces, and this document says so plainly.

1. **"Default role(s)"** — available once the folder's member group exists: the role(s) `<F> - members` holds **on `F`**. Set-valued, usually a singleton. Each entry is one row: `<F> - members × role × {F}`.
2. **"Shared with"** — the audience editor: rows of *(another folder's member group, role)* granting **on this folder**: `<other> - members × role × {this folder}`. Only **existing** member groups are selectable — if the audience folder's toggle is off, the admin enables it there first.

All resulting assignments are **ordinary, admin-owned, removable rows** — not builtin-protected, never re-created behind an admin's back — and **non-recursive**, which is load-bearing: a recursive one would expose descendant-folder content within the branch (a sensitive library loaded into a sub-folder would become readable by the whole branch), defeating placement-scoping. (A recursive exception for the directory was considered and rejected — see §4.4.)

**Fresh installs ship one decision, two rows** (and Global's member-group toggle on):

| Assignment | Role |
|---|---|
| `Global - members × Catalog Reader × {Global}` | **Catalog Reader** (`BI-RL-CAT`): view on all *definition* models — frameworks, matrices, threats, reference controls, terminologies, labels, asset classes, classification schemes (and levels), custom-field definitions, mapping sets, TTPs, document templates. |
| `Global - members × Directory Reader × {Global}` | **Directory Reader** (`BI-RL-DIR`): view on **User only**. All normal User reads expose the **safe projection** (picker fields); administrative metadata — MFA, IdP state, admin flags — is served exclusively by a separate administrative endpoint under its own permission. No serializer conditionality anywhere (role provenance is unknowable in the primitive). |

**Teams and entities are standard objects** — like applied controls: visible where roles reach, shareable downward via a folder's default roles or shared-with rows like any other content, never ambient by birthright. A shared vendor registry, where an organization wants one, is the shelf pattern (§5.4) — an administrator's choice, not a built-in. Their serializers are ordinary object serializers; hardening them is a product concern outside this specification. The Actor delegate needs no change: `readable(Actor)` = readable(User) ∪ readable(Team) ∪ readable(Entity), with the Team/Entity parts supplied by ordinary scoped roles.

**Built-in roles are semantically defined and tenant-immutable.** `Catalog Reader` *means* "may read catalog objects"; its permission list is the current answer to that semantic, not its identity. It evolves under exactly two rules: **(i)** a new model classified as catalog adds its view permission in the same release — no existing rows are exposed, but existing assignments **prospectively authorize all future rows** of the new model; this follows the semantic contract and is stated so nobody discovers it by surprise. A CI rule requires **every new securable model to be classified** — Catalog, Directory, Operational, or explicitly unclassified — so the decision is never made by omission. **(ii)** Reclassifying an *existing* model into a built-in role is an **access migration** — measured, reviewed, and release-noted with the same discipline as the seeding gates. There is no role versioning: one role, one meaning, fleet-wide. **Custom copies do not follow**: a custom role copied from `Catalog Reader` is a static permission set; upgrade reporting identifies custom roles containing catalog/directory/operational permissions so administrators can decide whether to extend them. Tenants never edit built-in roles (`Catalog Reader`, `Directory Reader`, `Operational Reader` — `BI-RL-OPR`: Asset, AppliedControl and its Policy proxy, Evidence, SecurityException, Vulnerability, Incident; documents and assessments deliberately excluded — and `Reader`); customization means replacing an assignment's role with a custom copy.

### 4.3 Invariants (each is a conformance test)

1. **No per-object visibility state exists anywhere** — no flag, no column, no property.
2. **No visibility-specific code exists in the resolver.** `readable(u, M)` ≡ `get_allowed_folder_ids(u, view_M)`; the target plan's overlay seam closes empty.
3. **RoleAssignment has no lifecycle state.** No enabled/status field; migration proposals live outside IAM until accepted (§6).
4. **Human role-assignment principals are exactly two kinds** — generated role×domain groups, and derived member groups. **Write-time validation is the primary enforcement**: serializer/model-level rejection of human direct-user principals, of kind-discriminator edits, and of out-of-toggle member-group lifecycle operations. Boot checks are a **detection backstop** whose failure behavior is start + alarm + repair guidance — data findings never refuse boot.
5. **Members groups are derived-only** (no UI/API mutates membership); existence obeys the toggle invariant (§4.1), with no dangling references.
6. **Identity gates ambience**: third-party principals, service accounts, and deactivated accounts never contribute to member groups; enclave exclusion is **positional, by path** (§4.1) — a property of grants, not an identity class. A service account gets explicit grants at creation, both offered default-checked: `Catalog Reader` and `Directory Reader` on Global (integrations reading frameworks or resolving users fail without them); its work access remains scoped roles via the machine-reserved direct path. With Directory Reader now User-only (#64), an integration resolving **Team- or Entity-backed owners** gets nothing ambient and needs scoped grants: existing accounts are protected by the exact-reach migration (§6.7); new accounts rely on the admin granting scoped access at creation.
7. **Content flows never create or modify IAM.** Loading a library or authoring definitions places content only (a passive informational note is permitted). Lifecycle features (publishing a document, issuing a finding) create an **independent, immutable published aggregate** (snapshot + manifest, per the findings roadmap) and **place** it where its audience already reads — never grants. Any future workflow that must create an assignment requires the IAM-administration permission explicitly.
8. **Components follow their aggregate root; delegates follow their delegatees** (Actor ≡ readable User ∪ Team ∪ Entity — §7.1). Nothing that is a component ever changes folder on its own.
9. **Role permission lists are the taxonomy.** Built-in role semantics are fleet-consistent; their permission lists are product-managed and may change only under the role-evolution rules (§4.2).

### 4.4 What was considered and rejected (for the archive)

- **Per-object flags** (`is_published`, rev. 2's `visible_to_descendants`): replaced by placement, default roles, and shared-with audiences. Evidence-gated reintroduction on one model stays possible.
- **The resolver overlay with per-model conditioning ("the amplifier")**: the last non-RBAC rule; traded for pure data. Its least-privilege function survives as expressible policy and as the migration equivalence measurement (§6).
- **Member-group lifecycles, three rejected variants**: reference-counted implicit existence; `create_iam_groups`-tied lifetime; default-role-bound existence (broken by the shelf pattern). The dedicated toggle supersedes all three; a referenced-block on toggle-off was rejected as not admin-actionable for a derived group.
- **Materialized membership**: rejected with its whole apparatus (synchronization, reconciliation, health flags, quarantine) in favor of virtual evaluation.
- **Role versioning** (`RoleVersion` or versioned Role rows): rejected as over-engineering; built-in roles are semantic (§4.2).
- **Role-provenance-dependent serializers**: unimplementable in the primitive; superseded by the universal safe User projection.
- **A recursive Directory-Reader exception** (to make domain teams/entities org-visible): rejected — non-recursion stays a blanket rule; teams and entities are standard objects instead (ruled: "like applied controls").
- **An "all active internal accounts" group**; **per-model mode enums, folder visibility flags, board-subdomains, twin `view_published_*` permissions, a global "everyone" principal, paradigm flags with legacy markers**: see the decision log.

## 5. Sharing patterns (how every use case is expressed)

1. **Org-wide catalog**: ships working — Global's default roles.
2. **Sensitive/domain catalog** *(follow-up feature — today `LibraryImporter` loads into Global only)*: load the library into the domain; then enable the domain's member group (if needed) and set its default role. The load itself never grants anything. The pattern applies today to domain-authored definitions (labels, asset classes, classification schemes, custom fields).
3. **Cross-domain operational composition**: `Operational Reader` among a folder's default roles, where wanted (migration seeds it only under the §6 equivalence discipline).
4. **The shelf pattern** (per-object sharing at folder granularity): create a sub-folder (`EMEA/Shared`), move the objects in, then on the shelf's **"shared with"** control add *(EMEA - members, reader role)*. If EMEA's member group doesn't exist yet, enable EMEA's toggle first. A shelf never inherits its parent's default; it always carries its own row. The same pattern serves a shared **vendor registry** (entities) or shared team rosters.
5. **Publishing a document / issuing a finding**: the lifecycle act creates an independent, immutable published aggregate and **places** it where its audience already reads (a shelf, the enclave, the portal). Placement, not grants.
6. **"Publish a risk analysis as a template"**: derive a frozen definition-kind copy (snapshot / library-builder path), place it; `Catalog Reader` does the rest.
7. **Audience-scoped sharing**: a shared-with row naming that audience's member group.
8. **Custom-field definitions and form rendering**: rendering-critical schema is UI configuration, not data. Form rendering consumes a **restricted form-schema projection** (name, type, choices) available to anyone who can view or edit the host object — independent of catalog grants — so configured fields are **never silently absent** from forms. Full `CustomFieldDefinition` objects remain RBAC'd like everything else.

## 6. Migration & transition

The migration must preserve **both** dimensions of today's behavior, and they are different measurements: **object visibility** (what content is exposed — preserved by seeds and compatibility rows) and **principal capability** (who may see which kinds — on main, the published mechanism was conditioned per user; a default role is not). Equivalence is proven per seed, **exhaustively — never sampled, never assumed**.

**Expectation, stated realistically:** `h > 0` is the norm, not the tail. The worked example is structural: the built-in internal-auditee role (`BI-RL-ADE`) holds `view_framework` and the TTP views but not matrices, threats, or reference controls — so **one auditee makes `h(Global, Catalog Reader) > 0`** for the whole tenant, and any custom role missing one catalog model does the same. The proposals-and-compatibility machinery below is therefore the **primary path**, not the exception path. Per explicit ruling, migration defaults are **deliberately deferred to fleet practice**: run the scans, observe the real distributions, then choose how aggressively to move tenants from compatibility rows to the clean built-in roles. The machinery supports every point on that spectrum.

1. **Two releases, normatively (staging is logically required).** **Release N** ships: the scan signals, the proposal store, the pre-flight command, and the write-time validators. **Release N+1** ships the destructive column drop, and **it is the N+1 migration that creates the seeds and compatibility assignments, atomically with the drop** — release N creates no grants of any kind (scans, proposals, validators, and UI only), so no capability changes while the published mechanism still runs. The N+1 migration **refuses to run** while unresolved proposals, unremediated preconditions, or a missing pre-flight report exist. Self-hosted installations run the same pre-flight in N, turning what would be three mid-maintenance-window halts into one early report.
2. **The pre-flight command** (release N) reports, per tenant: mixed publication cohorts (homogeneity assertion: `count(distinct is_published) <= 1` per migrated (folder, aggregate-root model) cohort — excluding the enumerated exception rows: **hand-hidden objects, hand-published records, and policy/standalone documents**, whose treatment is item 8); **human direct-user role assignments, with per-case remediation guidance** — lossless conversion exists only where the folder has generated groups for that role; otherwise the report says so and offers the options (enable `create_iam_groups` there, restructure, or accept a broader grant), with an assisted, explicit, per-row conversion tool; third-party principals holding effective membership in non-enclave generated groups (a loss class if built-ins replace compatibility rows — see item 5); existing service-account reach diffs (#57); and pending proposals.
3. **Per-seed, exact gates.** Every candidate seed — Global `Catalog Reader`, Global `Directory Reader`, and each folder's `Catalog Reader` / `Operational Reader` — is evaluated independently: `g(folder, role)` content signals (per role — operational content never justifies a catalog seed) and `h(folder, role)` capability signals, computed by exhaustive set comparison of old versus new `readable(user, model, folder)` while the flags still exist.
4. **Seeding decisions**: a seed with `h = 0` is created enabled. A seed with `h > 0` becomes a **proposal outside IAM**, enumerating **both gains and losses**, per named principal; it becomes ordinary assignments only on explicit, recorded acceptance — rejection leaves exact compatibility assignments in place (uniform for humans and machines — item 7 below). The proposal store itself is readable by operators and global administrators only.
5. **Continuity: nothing goes dark, nothing widens silently.** SaaS: operators clear proposals before deploying N+1 (fleet-deployment gating), with the migration's own refusal as defense in depth. Self-hosted: the migration generates **exact compatibility assignments** reproducing each generated role group's old reach — and **the old/new reach diff feeding the generator is computed over *all* models each role held view on: Team, Entity, documents, and records included**, while candidate seeds (item 3) are evaluated only on their own role's models. Whatever main made reachable downward that no seed covers — notably Team and Entity after #64 — is preserved by compatibility rows, not by seed gates. The compatibility label lives in migration metadata (authoritative) and the assignment's name/description (non-authoritative); RoleAssignment carries no provenance field. **The operator decision report and prepared rollback information are retained until the tenant's migration decision is resolved** — indefinitely for tenants that never accept, which is the intended, safe direction.
6. **Equivalence is time-of-migration, stated openly**: a member who joins *after* migration with a narrow role sees whatever the folder's seeded roles grant, where main's conditioned mechanism would have filtered by their role. That is the new model working as designed, permanent — the prospective-principal counterpart of §4.2's prospective-authorization statement.
7. **Existing service accounts** (#57/#58): per-account exhaustive old/new reach comparison; exact compatibility assignments by default; built-ins only via explicitly accepted, recorded widening; rejection preserves compatibility.
8. **Known, accepted deltas** (measured; artifact-dominated, single-object populations so far) — scoped precisely, since the comprehensive generator (item 5) leaves no delta on the compatibility path itself: **policy documents published downward** are a delta only where compatibility rows are declined in favor of seeds, or under the homogeneity exceptions (a role holding document views below otherwise gets its compat row); **hand-hidden operational objects** become visible under **any** new folder-level grant covering their folder — seed or compatibility row alike — which is precisely why the homogeneity gate halts on them first, forcing a tenant decision before either mechanism exposes them (the #4578 backfill precedent applies where exposure is chosen); **hand-published records** go dark only outside compatibility coverage. **Verified non-dependency, recorded**: third-party respondents never relied on the published mechanism — their enclave assignment is excluded by both of main's published branches (an intentional, tested invariant), and questionnaire content reaches them through aggregate-scoped nested serialization; nothing in this migration touches them.
9. **No domain-loaded libraries exist at migration time** (loading is Global-only today). **`SCHEMA_VERSION` bumps** with release N+1, so pre-upgrade backups are rejected cleanly.
10. **UI shipped with this work**: the member-group toggle, the "default role(s)" and "shared with" controls, the previews (toggle-off cascade, folder move), the pre-flight report — and one line in the service-account creation flow noting that Team/Entity-backed owner resolution requires scoped grants (§4.3-6). `DOMAIN_MEMBERS` groups are excluded from SCIM group listings (they are derived, not provisionable).

## 7. Immediate fixes on main (independent of the rest)

### 7.1 Actor picker asymmetry (a confirmed bug)

Actors are the pointer records behind owner, reviewer, and assignee fields; each wraps a User, a Team, or an Entity. On main, the Users page and the actor pickers disagree: the Users list applies the general visibility rule, published mechanism included, while the actor path (`_get_actor_accessible_ids_by_perm`) checks role assignments only. Verified by test: a domain-scoped analyst sees a root-folder colleague on the Users page, but that same colleague is absent from the analyst's owner pickers.

The fix applies invariant 8: for the view prefix, the Actor delegate returns the actors whose underlying User, Team, or Entity is itself viewable by the general rule; the point check `_is_actor_accessible` delegates to `is_object_accessible` on the underlying object. Paradigm-proof: whatever the resolver returns tomorrow, actors follow.

### 7.2 GlobalSettings permission cleanup

Reads of UI configuration — feature flags, general settings, vulnerability SLA — become plain authenticated endpoints with no model permission. Every session needs them, so no role composition may be able to break them.

`view_globalsettings` and `change_globalsettings` are removed from the non-admin built-in roles. The permission returns to meaning "administers instance settings", checked as `is_access_allowed(perm, root)`. Sensitive rows (sso, infra-config, sec-intel-feeds) become admin-only through plain RBAC; the bolt-on `IsGlobalAdmin` guards stop being load-bearing, and **the branch's** "sensitive settings MUST have extra checks" comment is deleted — the invariant moves from a comment into the permission model.

## 8. Impact on `feat/move_is_published_field_to_folder`

**Keep:** the full column-drop migrations (all models — shipped in release N+1); serializer/UI/test cleanups; the migration-graph repairs (automation dependency `0003_workflow_engine`; restore the deleted metrology 0005 migration); the SSO `IsGlobalAdmin` guard (until 7.2 lands); the GlobalSettings attribute-name fix.

**Remove:** `ViewableFromDescendantsMode` and all per-model mode attributes; `Folder.viewable_from_descendants` (field, migration RunPython, root-folder invariant, FolderForm checkbox in CE and EE, content-types endpoint parameter, i18n keys); the `_viewable_from_descendants` property; the ancestor-visibility blocks in `iam/models.py` (both copies) and the published branch of `core/permissions.py`.

**Add (release N unless noted):** the member-group toggle with cascade-preview-and-manifest and the **virtual membership evaluator** in principal resolution (§4.1) with its expansion property test and query-plan tests; **`manage.py check_iam_closure`** (detect + repair modes; CI and pre-flight — the promoted companion-plan deliverable); **write-time validators** (human direct-user rejection, kind immutability, toggle-lifecycle protection) with boot-check backstops (start + alarm + repair); the `Catalog Reader` / `Directory Reader` (User-only) / `Operational Reader` built-in roles; the "default role(s)" and "shared with" folder controls with their permission gate; the universal safe User projection + administrative endpoint split; the custom-field form-schema projection; scan signals `g(folder, role)` and `h(folder, role)` plus the third-party-membership and direct-user-row scans; the proposal store (operator/global-admin readable) and **pre-flight command**; the **assisted direct-user conversion tool** (§6.2); the compatibility-assignment generator (comprehensive across all models per §6.5); the service-account creation options and existing-account migration; the new-model classification CI rule; `SCHEMA_VERSION = 3` (release N+1, with the drop).

## 9. RAG / chat retrieval scope

1. Retrieval filters on `get_allowed_folder_ids(u, view_M)` — the same call every list view makes, through the same canonical membership expansion. Default-role and shared-with assignments carry the catalog into scope automatically; third parties and service accounts are scoped by their explicit grants.
2. Relevance stays a ranking concern (work folders vs catalog folders), never an access concern.
3. Entitlements and settings models are not indexed at all.
4. The critical test: every retrieved chunk's `(model, folder)` ∈ granted folders at query time.

## 10. Conformance matrix (final numbering, stable for implementation tickets)

1. `readable(u, M)` ≡ `get_allowed_folder_ids(u, view_M)` — no other **folder-visibility decision path** exists (the overlay seam is empty). Nested serialization rides the host object's check (§4) and is tested as such, not counted as a second path.
2. No model carries visibility state (schema scan); RoleAssignment carries no lifecycle or provenance field.
3. Member-group existence ⇔ toggle on, both directions; no assignment references a missing group; the group stores no membership rows; enclave folders cannot enable the toggle.
4. Toggle-off cascades: deletes the group, its default-role rows, and all shared-with rows referencing it — impact preview shown, audit event emitted, restorable manifest stored; restore recreates exactly the removed assignments by natural key, skipping and reporting rows whose target folder no longer exists.
5. Clearing a folder's **default roles** deletes only those rows — shared-with assignments referencing its member group elsewhere are untouched.
6. Third-party, service-account, and deactivated principals never contribute to member groups; deactivation (including expiry-driven, via the scheduled task) takes effect on the first evaluation after commit; enclave exclusion holds for nested-enclave paths.
7. Multi-path membership: a user reachable through several effective source paths (direct, IdP-mapped, multiple groups) remains a member until the last path is gone — covered for direct removal, IdP mapping deletion, and `idp_groups` flag changes (a flag change affects effective assignment reach; RoleAssignment rows are unchanged).
8. Human role-assignment principals are exactly the two allowed kinds — **rejected at write time** (serializer/model); the boot check is a backstop that alarms and guides repair, never refuses boot on data findings; derived member groups never appear in their own derivation source.
9. A user in no managed group sees nothing.
10. `readable(Actor)` ≡ actors backed by readable(User) ∪ readable(Team) ∪ readable(Entity) (§7.1).
11. All normal User reads expose only the safe projection, for every caller; administrative metadata requires the administrative endpoint and permission. (Team and Entity are standard objects; no ambient grant exists for them.)
12. Default-role and shared-with edits change visibility for exactly the target folder (non-recursive), create/delete exactly the projected rows, and require the IAM-administration permission.
13. A shelf sub-folder never inherits its parent's default-role assignment.
14. Folder move: the move and its closure update are atomic; membership is reflected by the next evaluation with no membership-specific step; an audit event lists affected groups and assignments; cross-folder audience references are preserved (or explicitly retired on folder deletion, with preview and audit).
15. Content flows and lifecycle features perform zero IAM writes (grep-able + integration test); published aggregates are independent immutable roots.
16. Custom-field form-schema projection: a host's form renders all applicable definitions for any user who can view the host.
17. Migration: per-seed exact equivalence (`h(folder, role) = 0` ⇒ identical old/new `readable`, by exhaustive set comparison); `h > 0` candidates exist only as proposals outside IAM, enumerating gains **and** losses, until explicitly accepted — rejection leaves exact compatibility assignments; the destructive migration refuses to run with unresolved proposals, failed preconditions, or no pre-flight report.
18. Upgrade preconditions halt with a report: mixed publication cohorts (homogeneity), and human direct-user role assignments — each with per-case remediation guidance; no silent conversion path exists.
19. Existing service accounts: exact compatibility by default; built-ins only via accepted recorded delta; neither silent widening nor access loss for any machine principal.
20. Virtual membership: engine expansion ≡ independent reference recompute (property test); deduplicated; query plans tested on deep trees and many-group users; ≤1 additional indexed query per principal resolution; request-scoped memoization permitted, cross-request caching absent initially.
21. The member-group kind discriminator is immutable and the sole trigger of special behavior; `DOMAIN_MEMBERS` groups are created/deleted only via the toggle; folder binding never reassignable; excluded from SCIM group listings.
22. No code path joins the raw membership table for member groups — all consumers use the canonical expansion helper (static check + integration test).
23. Effective group membership (direct ∪ IdP-mapped) is one shared relation consumed by principal resolution and the evaluator — a user reachable only via an IdP mapping appears exactly where a directly-added member would.
24. `check_iam_closure` exists, runs in CI and pre-flight, and is load-bearing for membership: a corrupted closure is detected by it, and the membership property test fails against a closure-free reference recompute.
25. Every new securable model carries a classification — Catalog, Directory, Operational, or explicitly unclassified (CI check); unclassified-by-omission fails the build.
26. Built-in roles reject tenant edits; product changes to their permission lists contain only new-in-release models or carry an access-migration marker.
27. The proposal store is readable by operators and global administrators only.
28. `makemigrations --check` clean; write-time validators active; boot backstops green.

## 11. Decision log

| # | Decision | Ruling |
|---|---|---|
| 1 | Concept of downward visibility for shared content | Keep — expressed as data, not mechanism. |
| 2 | Implicit per-object flags on 158 models, set by code | Removed. |
| 3 | Per-model mode enum / folder flag (the reviewed branch) | Rejected. |
| 4–5 | Full-visibility paradigm; bulk private-subdomain migration | Superseded / retired unbuilt. |
| 6 | Amplifier conditioning | Removed — traded for pure-RBAC expressiveness; survives only as the migration equivalence measurement. |
| 7 | Global "everyone" principal | Superseded by `Global - members`. |
| 8 | `view_published_*` twin permissions | Rejected. |
| 9 | Hand-hidden / hand-published objects on main | Measured (fleet scan): artifact-dominated, single objects; deltas accepted per tenant. |
| 10–15 | ClassificationLevel, mapping sets, Preset, export templates, DocumentTemplate, Tactic/TTP | Encoded in role permission lists: catalog content in `Catalog Reader`; Preset/LibraryDraft/export templates in no seeded role. |
| 16 | Records (acceptances, issues, metric instances) | In no seeded role; shared via shelves or shared-with rows. |
| 17 | GlobalSettings | Authenticated endpoints for benign reads; permission stripped from non-admin roles (§7.2). |
| 18 | Actor asymmetry | Current bug on main; fix first (§7.1). |
| 19 | Building analogy | Documentation only; never code vocabulary. |
| 20 | RAG scope | Granted folders — the only set there is. |
| 21 | Object-level visibility flag | Not built; every use case has a data expression (§5); evidence-gated reintroduction possible. |
| 22 | Operational objects | `Operational Reader` among default roles where wanted; migration-seeded only under the equivalence gates. |
| 23 | Finding / RiskScenario | Distribution belongs to the findings lifecycle — by placement (#36/#46). |
| 24 | "Publish a risk analysis as a template" | Derive a frozen definition copy and place it. |
| 25 | Field naming (`visible_to_descendants`) | Moot — not built. |
| 26 | Member groups as the foundation | `<domain> - members`, derived; completeness via effective membership (#53) and the two-kinds rule (#44). |
| 27 | Root exception | Dead — Global is just the top folder whose toggle and default roles are set at install. |
| 28 | Migration continuity roles | Atomic `Catalog Reader` + `Operational Reader`, composed as default roles — subject to the equivalence gates. |
| 29 | The transparency dial | The folder's default role set — atomic, tenant-immutable roles, administered as ordinary rows. |
| 30 | Fresh-install seeding | Global only: toggle on, `Catalog Reader` + `Directory Reader`. Below Global, nothing. |
| 31 | Content flows and IAM | Content flows never create or modify IAM; passive notes only. Extended by #36 to lifecycle features. |
| 32 | The folder controls | Projections of assignment rows — no stored visibility fields; new IAM UI surfaces, gated by IAM-administration permission. |
| 33 | Migration seeding policy | Equivalence-gated per seed; "nothing observable changes" withdrawn as a blanket claim. Refined by #41, #62. |
| 34 | Members-group lifecycle (final) | Explicit toggle: on ⇒ exists; off ⇒ cascade with preview, audit, restorable manifest. Three alternatives rejected. |
| 35 | Catalog / Directory split | Separate roles; Directory narrowed to User-only by #64. |
| 36 | Lifecycle features act by placement | Published aggregates placed where the audience reads; zero lifecycle IAM writes. |
| 37 | Custom-field rendering | Restricted form-schema projection; never silently absent. |
| 38 | Built-in roles: semantic identity, tenant-immutable | Role versioning rejected; new catalog models join by semantic (prospective authorization stated); reclassification = access migration; custom copies are static. |
| 39–41 | Materialized-membership integrity; the "shared with" control; per-seed exact gates | #39 superseded by #49; #40–41 as stated in §4.2/§6. |
| 42 | h > 0 continuity strategy | Proposals + compatibility rows; **resolved by #62**: defaults deferred to fleet practice ("we'll see in practice, and we will adapt"). |
| 43 | Universal safe directory projection | All normal User reads are the safe projection (provenance unknowable); admin metadata behind separate endpoint. |
| 44 | Principal-kinds invariant | Two allowed kinds; derivation sources = generated groups only; **write-time validation primary, boot check backstop** (#61). |
| 45 | Homogeneity precondition | `count(distinct is_published) <= 1` per migrated cohort; violations halt with report and remediation. |
| 46 | Published aggregates | Independent immutable snapshot + manifest, placed at audience location. |
| 47–48 | Architectural approval; final precision edits *(historical)* | Rev. 3.2/3.3 milestones; role versioning later superseded by #38. |
| 49 | Virtual membership evaluation | One derived-principal expansion rule in group resolution; no materialized rows; no authorization-decision primitive added. |
| 50–52 | Implementation baseline; virtual-evaluation hardening; rev. 3.4 precision *(historical)* | Absorbed; superseded in detail by rev. 3.5 below. |
| 53 | SCIM / IdP-group completeness | Effective membership = direct ∪ IdP-mapped (flag-gated), one relation for resolution and derivation. |
| 54–58 | Freeze, acceptance clarifications, service accounts *(historical)* | The rev. 3.4 freeze was superseded by the fifth review round; content preserved in §4/§6. |
| 59 | **Rev. 3.5 re-stamp and change control** | The fifth (code-verified) review round is absorbed as a proper revision; "frozen" now means it: further changes are new ADRs, implementation issues, or threat-model findings — never edits here. |
| 60 | **`check_iam_closure` is a build item, not an existing tool** | The spec wrongly called it existing; it is a companion-plan cross-cutting deliverable, promoted to a hard dependency with defined scope (detect + repair, CI + pre-flight, alert-and-repair on corruption). The reviewer's sub-claim that the companion plan never mentions it was itself incorrect (its §5 does). |
| 61 | **Facts vs targets; enforcement shape** | §2 restated as facts about main only; the two-kinds rule enforced at write time (serializer/model), boot checks demoted to alarming backstops; direct-user remediation guidance acknowledges the no-lossless-path case with an assisted conversion tool. |
| 62 | **h > 0 is the norm — observe, then adapt** | Verified structurally (auditee role). Migration framing rewritten around proposals-as-normal; two-release staging (scan/proposals/pre-flight in N, drop in N+1) made normative; defaults deliberately deferred to fleet data per explicit ruling. |
| 63 | **Loss accounting completed** | Proposals enumerate losses as well as gains; pre-flight scans third-party principals in non-enclave groups; prospective-principal permanence stated (§6.6); respondent non-dependency recorded as verified. |
| 64 | **Directory Reader = users only** | Ruled: "Teams and Entity are standard objects, like applied controls." C1 coverage and C2 exposure dissolve; vendor registry = shelf pattern; recursive directory exception rejected; Team/Entity serializers out of scope. |
| 65 | **Enclave member-group toggle forbidden** | Enclaves receive explicit grants only. |
| 66 | **Operational precision** | Manifest restore by natural keys with skip-and-report; cascade preview authority defined (audience-folder admin sees affected rows; affected-folder admins notified via audit); performance budget normative (≤1 indexed query; request-scoped memoization permitted); `DOMAIN_MEMBERS` excluded from SCIM listings; proposal store operator/admin-only; expiry enforced via the deactivation task; §7.2 comment attributed to the branch; nested serialization recognized as a host-checked visibility path (row 1 scoped accordingly). |
| 67 | **Rev. 3.5 completion — generator comprehensiveness** | The compatibility generator's reach diff is computed over **all** models each role held (Team/Entity/documents/records included); candidate seeds measure only their own role's models — so #64's ejection of Team/Entity from seed roles is safe by construction. §6.8's deltas rescoped to the non-compatibility paths (resolving the apparent §6.5/§6.8 contradiction); rollback-retention commitment restored; assisted conversion tool build-listed; SA Team/Entity-resolution note added; stale #58 citation fixed. |
| 68 | **Rev. 3.6 — terminal wording repairs; freeze in force** | Homogeneity exception rows re-enumerated in §6.2 (hand-hidden, hand-published, documents); hand-hidden delta rescoped to any folder-level grant with the homogeneity gate as the actual guard; seed/compat creation pinned to the N+1 migration, atomic with the drop (release N creates no grants); SA-UI note relocated to §6.10; rollback retention worded as until-decision-resolved (indefinite for never-deciding tenants, deliberately). Per the reviewer: nothing further — continued review yields diminishing returns; implementation decomposition is the next step. This is the last row created by editing this document. |

## 12. Design principles distilled

1. **One primitive.** If a capability can be expressed as groups, roles, and assignments, it must be. The count of visibility-specific mechanisms in this design is zero, and RoleAssignment has no lifecycle states.
2. **Defaults are data; existence is a decision.** The member-group toggle, the default roles, and the shared-with audiences are explicit, removable administration — with previews, manifests, and audit where removal cascades.
3. **Invariants live in structure** — write-time validators first, boot checks and integrity commands as detection backstops, conformance tests always — never in comments, save hooks, or conventions.
4. **Derived semantics must be independently verifiable**: property-test the virtual expansion against a reference recomputation, enforce closure integrity in production, and keep no separately synchronized membership state.
5. **Identity gates ambience; position gates enclaves**: third parties, machine principals, and deactivated accounts get exactly their explicit grants; enclave exclusion is a property of paths, not of people.
6. **Components follow roots; delegates follow delegatees; nested content rides its host's check.**
7. **Placement scopes reference material; default roles and shared-with audiences share work; lifecycles act by placement; IAM is written only by administrators and the accepted parts of the install/upgrade seeding.**
8. **When an object seems to need special visibility treatment, first check whether a permission is doing double duty** (the GlobalSettings lesson). When a principal seems to need special directory treatment, first check whether it is simply a standard object (the Team/Entity lesson).
9. **Capability-changing steps are measured exactly before they are claimed** — object fidelity and principal-capability equivalence are separate, exhaustive measurements; destructive steps ship one release behind their measurements; and claims of continuity are scoped to what the measurements actually prove.
