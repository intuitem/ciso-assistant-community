# Remove all `is_published` fields; visibility becomes a folder default role in a three-layer IAM model

- Status: Accepted
- Date: 2026-09-05
- Deciders: @eric-intuitem, @monsieurswag, @nas-tabchiche
- Supersedes: the member-group/projection design explored in `documentation/architecture/iam-refactor/review-iam-and-scoping.md` (kept as the analysis record; the guardrails it specified are retained here)

## Context

Some objects must be visible from descendant domains without a role assignment there — catalogs, shared vocabularies, the directory. The `is_published` boolean that implemented this sat on 158 models with per-model defaults that disagreed, was written by four different code paths (per-model `default=True`, forced flags in `save()`, the library loader, `PublishInRootFolderMixin`), was never exposed in any UI, and had no revocation story. Most models never needed it; the few that did could not be operated by users.

A detailed specification (`review-iam-and-scoping.md`) explored replacing it with derived member groups projected through ordinary role assignments. This ADR adopts that specification's *semantics and guardrails* but not its machinery: the same access rules are expressed with one nullable column and one derivation rule, instead of a new principal kind with its own lifecycle.

## Decision — the three-layer model

### Layer 0 — the role-assignment kernel (stable; we do not expect to change it)

A `RoleAssignment` is a tuple *(principal, role, perimeter folders, is_recursive)*. Every access question is answered by the single primitive `is_access_allowed(permission, folder)` (or its bulk form). The kernel carries **no identity rules and no visibility rules**: it does not know what a third party, a service account, or a "standard" group is. Anything expressible as assignment rows requires no kernel change; a planned evolution that would require one has been mis-scoped.

### Layer 1 — the usage discipline (may evolve)

The product uses the kernel in one specific way, through two provisioning modes that are duals of each other:

- **`Folder.create_iam_groups` — recursive mode, downward.** Per-folder generated groups with role assignments recursive over the subtree. Membership is explicit: users are placed in groups to get rights.
- **`Folder.default_role` — non-recursive mode, upward.** A nullable FK to a `Role`. The folder grants that role, **non-recursively, on itself only**, to its *members*.

**The definition, structural and identity-free:**

> **Every domain has members: the people its own and its sub-domains' IAM groups grant roles to.**
> **The default role is what the domain grants its members — on the domain itself.**

The mechanics are the same idea seen from the grant's side: **a role granted through a standard IAM group also carries the default role of its perimeter domain and of every domain above it** — a third-party workspace boundary stops the climb. The ambient right travels with the grant, not with the person: for everything the product provisions a group's assignment covers its own folder, and if an administrator points an extra assignment of a group at another branch, its members pick up that branch's default roles with it — the reach moved, and the ambient right moved along.

Every exclusion is a corollary of the definition, never a special case:

- **Service accounts** hold direct role assignments — no group grants them anything, so nothing carries anything: an integration reads exactly what its own assignment names (least privilege by design).
- **Third parties** hold their grants inside third-party workspaces, where the climb stops → never members of any domain.
- **Direct or custom-group grants** give exactly what they name, nothing ambient. Direct human assignments are forbidden outright (validator below): group membership is the only rights path for humans, which is what keeps "members" the whole story.

**Defense-in-depth:** the audience evaluator additionally excludes `is_third_party` users. This protects the convention against data that predates or escapes the validators; it is a layer-1 backstop, not a kernel rule.

**Placement invariants — enforced by write-time validators:**

1. Internal human users hold rights via group membership only; direct human role assignments are rejected.
2. Service-account users are never added to user groups.
3. Third-party users are placed only in enclave groups.

**Default-role constraints:**

- A role is eligible as a default role only if it contains **`view_*` permissions exclusively**. Enforced when the default role is set *and* when a role already in use as a default role is edited.
- **Enclave folders may not carry a default role** (rejected at write time).
- The grant is non-recursive by construction: it applies to the folder itself, never its subtree. (A recursive default role would expose descendant content to the whole branch, defeating placement scoping.)
- **Default-role grants surface wherever grants are displayed** — the role-assignments register and per-user permission views must tell the whole truth. The column is the storage; the register is the presentation. Without this rule the product would have two grant sources and one access map.

### Orthogonal — account lifecycle

`is_active` is not an access rule. Authentication refuses inactive users a session, so request-time resolution never sees them; roster-style displays (member lists, seat counting) filter on it explicitly. Expiry-driven deactivation inherits the same story via the scheduled task.

## Formal properties (each is a conformance test)

1. **Additive and monotone.** No deny rules; grants compose by union — no precedence, no ordering effects.
2. **Revocation-complete.** Rights exist only while their structural cause exists; removing a membership, assignment, or default role removes everything derived from it at the next evaluation.
3. **Well-founded.** Default roles grant *permissions*, never *memberships*, so audience derivation is a single pass with no feedback loop. A proposal for a default role that grants membership in anything breaks this property and requires a new ADR.
4. **Reconstructible.** Audiences are derived from audit-logged structure, so "who could see folder F on date D" is recomputable from history.
5. **One decision primitive.** `is_access_allowed(perm, folder)` remains the only access question; the two modes only change how the allowed-folder set is populated.

## Standard postures

Two tenant-immutable builtin roles, whose permission lists live in `core/startup.py` and are re-synced at every boot (the lists there are the source of truth; migration-time copies are initial values only):

- **`BI-RL-CAT` (Catalog reader)** — the reference material an organization shares with itself, plus the directory and folders. The fresh-install default role at Global.
- **`BI-RL-MIG` (Legacy migration reader)** — a frozen compatibility role approximating what `is_published` exposed in practice, assigned by the upgrade migration to eligible folders (enterprise edition only — see below). **No new model ever joins it**; tenants are expected to move to `BI-RL-CAT` or a custom role.

## Edition split

- **Community edition — the default role is hard-coded.** The root folder carries `BI-RL-CAT`, re-pinned by `startup()` at every boot; the folder serializer does not expose the field; no other folder ever carries a default role; and the upgrade migration writes no per-folder posture. Consequence for upgraded CE tenants: domain-level ambient visibility that `is_published` used to provide disappears — only the root catalog remains ambient. The roles endpoint is read-only in CE (it serves the default-role display); custom-role management is not a CE feature.
- **Enterprise edition — the default role is configurable.** The folder form exposes the control under the validators above; a fresh install starts with the root row only; the upgrade migration additionally sets `BI-RL-MIG` on every folder holding at least one published object of a legacy-list model. The control is a dial: administrators may replace any folder's default role with a narrower view-only role, or clear it — clearing the root's yields a fully explicit-grant posture with no ambient visibility anywhere. Custom-role create/update/delete (with per-folder group provisioning and license-seat enforcement) stays enterprise-only: the enterprise build registers its own roles viewset over the community read-only one.

## Consequences

- 158 `is_published` columns and their four writer mechanisms are removed; ambient visibility becomes one explicit, removable, auditable folder control.
- **The upgrade changes effective access in both directions, and release notes must say so:**
  - *Widenings:* per-object flags become per-folder-per-model grants (a previously unpublished object in a marked folder becomes visible); and the old resolver filtered ambient visibility by the caller's own permissions ("the amplifier") — that filter is gone, so any member of the audience receives the whole default role.
  - *Narrowings:* models absent from `BI-RL-MIG` (notably security exceptions, incidents, timeline entries, risk acceptances, documents) are no longer ambient anywhere. Their inclusion or exclusion is a deliberate product decision recorded with the role's list, not an accident of migration code.
- **Placement is audiencing.** Moving an object to another folder changes who can see it; folder moves are security-relevant acts.
- **Accepted limits** (deliberate, not oversights):
  - Folder granularity only. Per-object sharing is the *shelf pattern*: move the objects to a sub-folder and grant that sub-folder to its readers.
  - The audience is blunt: any membership below, however narrow, joins it. Mitigation is choosing a narrower default role, never per-user conditioning in the resolver.
  - No cross-branch audiences: sharing sideways is explicit grants on the holding folder.

## Evolution path

Layer 0 is frozen. Layer 1 may evolve — e.g. per-role group provisioning (recursive or not), or eventually free-form role assignments. **Every layer-1 evolution is an access-semantics change** and re-decides the audience definition deliberately, with the same disclosure discipline as this migration. The known fork: if direct human assignments are ever allowed, whether they count toward member audiences must be decided then. The enclave exclusion (positional) and machine exclusion (structural) survive all such evolutions; the third-party placement rule is a convention and keeps its validator in every future.

## Alternatives considered

- **Keep per-object flags** — failed empirically (see Context); no revocation story.
- **Per-object ACLs** — maximally expressive, unauditable at GRC scale.
- **Materialized/derived member groups with the default role as a projection of an assignment row** (`review-iam-and-scoping.md`) — same semantics; its extra machinery (a derived principal kind, lifecycle discriminators, projection invariants) buys grants-as-literal-rows. We retain that auditability requirement as the presentation rule (grants must surface in the register) at a fraction of the cost. Re-materializing later remains possible without semantic change.
- **`Folder.published_models` M2M (folder → ContentType)** — too complex, would slow IAM queries.
- **`Folder.stop_published_propagation`** — high implementation cost for little benefit; enclaves already exist.

## Security considerations

Administrator care plus a UI help message would not be a sufficient control: non-recursion bounds the *scope* of a default role to one folder, but says nothing about *capability* — an unrestricted default role carrying change/delete permissions would let one domain manager turn every user below into a writer on the domain. The controls are therefore structural:

- **View-only eligibility** forecloses write escalation; the worst misconfiguration is over-*reading*, which is recoverable.
- **The enclave prohibition** keeps visitor spaces free of ambient audiences.
- **The placement validators** keep machines and third parties out of audiences by construction; the `is_third_party` evaluator check backs them up.
- Residual risk — over-broad reading via the blunt audience — is bounded by role choice and disclosed in the UI. The help message informs; it is not a control.
