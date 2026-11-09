# Restrict token credentials with progressive delegation

- Status: Proposed
- Date: 2026-11-09
- Deciders: @eric-intuitem
- Related: [mcp-app-access-model](mcp-app-access-model.md) (how MCP is served and plugs into this model), [service-accounts-composition](service-accounts-composition.md), [global-user-creator-role](global-user-creator-role.md)

## Decision

**A person can delegate a subset of their existing rights to a token credential, using simple restrictions: which operations (create, read, update, delete) are allowed, by default and per domain. A delegation can never grant rights the person does not have.**

Three independent sources of authority decide together:

1. **The person's authority:** their current RBAC rights, what they may do.
2. **The person's delegation:** a default selection and domain overrides, what they chose to allow the delegate.
3. **The organization's policy:** for an app connection, the connection profile, what the organization currently permits for that app.

**Effective rights = RBAC ∩ delegation ∩ profile**, with control-plane and non-delegable operations always excluded.

Each source can be tightened independently, and none can grant what another refuses. RBAC remains the source of authority.

Six rules define the decision:

1. **Browser sessions are unchanged.** People continue to act with their existing RBAC rights.
2. **Existing credentials keep today's behavior.** They are marked unfiltered. Backward compatibility is mandatory.
3. **New credentials default to a delegation.** Unrestricted access (the legacy behavior, administration included), displayed as **Unrestricted (including administration)**, remains available as an explicit choice. One compatibility exception: an API request that omits the delegation field still creates an unrestricted PAT, until step 2's administrator policies change that.
4. **Control-plane operations are never delegated.** A delegation covers data only: no administration of users, access, domains, settings or integrations.
5. **Credential management is non-delegable.** A delegated credential cannot mint credentials, change passwords or MFA, or manage other credentials.
6. **The backend enforces delegations and fails closed.** A delegated credential without a valid authorization context is refused.

We will implement this incrementally, beginning with the MCP server. Each step has an explicit security guarantee.

## Context

Today, authorization is entirely RBAC-based.

Roles contain Django permission codenames (`view_`, `add_`, `change_`, `delete_`, plus custom permissions) and are assigned on folders. `RoleAssignment.is_access_allowed` and `RoleAssignment.get_allowed_folder_ids` are the main access-control functions.

A browser session, personal access token (PAT), service account, or OAuth token inherits its principal's full rights.

This creates a credential-escalation problem. For example, the OAuth token of an admin-registered app, whatever its user's role, can call `POST /api/iam/auth-tokens/` to create a PAT with that user's full rights and a ten-year expiry. That PAT keeps working after the original app connection is revoked.

The forthcoming MCP server (PR 5242) makes the problem more important. It handles tokens belonging to many users, and an AI assistant often needs much less access than its user. The frontend, which sees every session token and every password typed at login, is exposed in the same way.

We want to limit the consequences of a compromised integration or frontend, with the backend as the last line of defense, while preserving existing API integrations.

### Constraints

- **No breaking changes.** Some customers manage their entire instance through administrator PATs or service accounts. They must remain supported.
- **Least privilege by default.** New credentials should normally be restricted.
- **Understandable by the person delegating.** Restrictions use concepts users already know, domains and create/read/update/delete, not permission codenames, roles or technical scopes.
- **Microsoft-aligned model.** Reuse the concepts and vocabulary of Entra ID and Azure RBAC where they fit.
- **Incremental delivery.** MCP must be able to ship before the complete authorization system is implemented.

## Target model

The end state follows Microsoft's Zero Trust principles: **verify explicitly** (each request is decided from the credential that carries it), **least privilege** (a credential gets what its delegation allows, never more than its principal), **assume breach** (a stolen or misused credential stays bounded).

- **People** sign in through the browser and act with their RBAC. A later ADR covers step-up authentication and time-limited activation of control-plane roles.
- **Workload identities** are service accounts. They act as themselves, with their own role assignments, optionally narrowed by a delegation of the same shape, and get their credentials from their client registration.
- **Delegated credentials** act on a user's behalf: app connections, granted on the consent page, and PATs. Each one holds a delegation and an expiry, and can do what its user's RBAC allows within the delegation. Unrestricted access (the `unfiltered` flag) is the equivalent of Azure's `user_impersonation`, kept for existing credentials and for explicit choices.
- **Apps identify themselves with Client ID Metadata Documents (CIMD)** where they support it. This is the registration the MCP specification recommends, and it gives each app a stable identity, an HTTPS URL, that consent policies can name. Dynamic client registration stays for compatibility with clients that need it, such as Copilot Studio.
- **Every decision is made in the central access functions**, and every token is looked up on each request, so revoking a credential or disabling a user takes effect at once.

## Consequences

### The delegation model

A delegation is one structure: a **default** selection of operations, and optional **overrides** for specific domains.

```yaml
delegation:
  default: [read]
  overrides:                 # keyed by folder ID, shown here as paths
    Paris: [read, create]
    Paris/Finance: [read]
    Lyon: [read, update]
```

The delegate can read everywhere the delegator has access, additionally create in Paris (except Finance), and update in Lyon.

- **Overrides apply recursively** to the domain and its subdomains, unless a more specific override applies. The most specific one wins, and it may be more permissive or more restrictive than its parent. It never exceeds the delegator's RBAC, nor, for an app connection, the profile cap.
- **The default is not a maximum.** Overrides may exceed it when the delegator explicitly configures them. The connection profile remains an independent maximum for every domain.
- **An empty selection explicitly denies** all data-plane operations where it applies. **An absent override means inheritance**, not denial.

**Levels are an interface concept.** The interface presents the structure progressively; the level is derived from it, never stored, and authorization never depends on it:

| Level | Structure |
|---|---|
| 0 — full data-plane delegation | the default holds all four operations, no overrides. Since every delegable permission maps to create, read, update or delete, this is every data-plane operation the delegator can perform |
| 1 — global CRUD restrictions | any other default, no overrides |
| 2 — domain-specific restrictions | one or more overrides |

**Evaluation.** For each operation, the backend:

1. Determines the delegator's current RBAC rights.
2. Finds the rule for the target domain: the nearest override, or the default when none applies.
3. Checks whether the requested operation is allowed by that rule.
4. For an app connection, applies the profile cap (see below).
5. Refuses control-plane and non-delegable operations, whatever the delegation.

**Principles.** Restrict-only; dynamic (changes to the delegator's RBAC rights affect the delegate at once); simple by default (most users need only level 0 or a default selection); progressively precise (overrides are optional); recursive; administration and credential management excluded everywhere.

### Principals and credentials

| Credential | Principal | Delegation |
|---|---|---|
| Browser session | Signed-in user | Never |
| PAT | User | Optional; a preset by default |
| Service account | Service account itself | Optional; narrows its own RBAC |
| OAuth app connection | Consenting user | Chosen during consent |
| SCIM token | Unchanged | Not covered by this decision |

PATs and app connections use **delegated permissions**: they act on behalf of a user. Service accounts use **application permissions**: they act as themselves, using their own role assignments, and the same delegation structure can narrow those.

### Operations and planes

Each permission maps to one operation and one plane. The mapping lives in a registry.

| Permission | Operation |
|---|---|
| `view_*` | Read |
| `add_*` | Create |
| `change_*` | Update |
| `delete_*` | Delete |
| Custom permissions, such as `approve_riskacceptance` | Mapped one by one in the registry, or marked non-delegable. An unmapped custom permission is non-delegable |

Planes classify **individual permissions, not entire models**: a model can have both data-plane and control-plane operations.

| Plane | Operations |
|---|---|
| **Data** | Business data and reference data; reading users, groups, roles and folders |
| **Control** | Administrative changes to identity, access, folders, configuration and integrations; sensitive configuration reads |
| **Non-delegable** | Credential management and protected account operations |

**Control-plane permissions** include:

- Creating, changing and deleting users, user groups, roles, role assignments, IdP groups and folders.
- Managing global settings, SSO configuration and mailer configuration.
- Managing integration configurations, their synchronization models and webhook endpoints. Webhook endpoints are a standing channel for data to leave the instance.
- Reading integration configurations, webhook endpoints, SSO settings and mailer configuration, because they may contain secrets.

**Data-plane permissions** include:

- Operations on business data.
- Operations on shared reference data in the root folder: frameworks, libraries, risk matrices, threats, etc.
- Reading users, groups, roles and folder structure, which tools need to work.

**Non-delegable actions** include:

- Managing PATs, SCIM tokens, service accounts, OAuth clients, app grants and connection profiles.
- Changing passwords or MFA and other protected account-management operations.
- The self-service credential and session endpoints listed under Enforcement.

A delegation only ever covers data-plane permissions. Any permission not yet classified is treated as control plane, so no delegation reaches it. New data-plane permissions join the operation they map to: a delegation that allows Read covers reads added in later releases, once a developer has classified them. The registry is the review gate.

### No delegation is different from level 0

Only the explicit `unfiltered` flag means that a credential has no delegation. The flag is non-null and defaults to `false`. The migration sets it to `true` for existing credentials; otherwise only an explicit choice sets it.

| Stored state | Meaning |
|---|---|
| `unfiltered: true` | Unrestricted: legacy RBAC behavior, including control-plane operations |
| Level 0 (default holds all four operations, no overrides) | Every data-plane operation the delegator's RBAC allows; no control-plane or non-delegable operation |
| Empty default, no overrides | No allowed operation |
| Missing or malformed delegation | No permissions, or authentication refused |

An unfiltered credential preserves today's behavior, including operations outside the new registry. A delegated credential never silently becomes unfiltered because of missing data.

Because control-plane operations are never delegated, automation that must administer the instance, such as an external management system, uses an unrestricted PAT or an administrator-created service account with its own RBAC.

### Storage, presets and the profile cap

| Credential | Delegation stored on |
|---|---|
| PAT | `PersonalAccessToken` |
| Service account | `ServiceAccount` |
| App connection | `AppGrant`. It stores the default consented to, the overrides and the `unfiltered` flag; its `ConnectionProfile` provides the current preset |

Presets are named default selections: **All data** (level 0), **Read**, **Read and create**, **Read, create and update**, **Read, create, update and delete**. Administrators can define additional presets; together, the presets offered form the app consent policy. The consent page offers presets; overrides are edited afterwards on the credential.

**Update and delete require read.** The backend fetches an object through read visibility before changing or deleting it, so the interface adds Read whenever Update or Delete is selected.

**The profile cap.** For an app connection, the connection profile caps every rule: **effective(d) = RBAC(d) ∩ rule(d) ∩ profile**, where rule(d) is the nearest override or the default consented to. The default is not a maximum: an override is intersected with RBAC and the profile, never with the default. An override can only be set within the preset in force at that time. Tightening a shared profile applies to every connection using it at once. Widening or restoring it may give back rights an owner explicitly chose and a tightening had suspended, but never anything the owner has not chosen; rights beyond the owner's choices need a consent renewal or an edit by the delegator.

**From step 1a, changes take effect on the next backend request:** the backend resolves the current grant and profile on each request; it does not capture permissions when an OAuth token is issued. MCP v1 is an exception: the backend does not enforce delegations yet. The MCP server does, and its introspection cache can delay a change by about a minute. Revoking a connection remains immediate, because the backend checks the token itself on every call.

Existing PATs, service accounts and administrator-registered app connections migrate with `unfiltered: true`. This follows the pattern used when SSO email trust was introduced. New PATs default to a preset in the UI; the API exception is stated in the Decision. Credential expiry remains unchanged: PAT expiry, service account `expiry_date`, and OAuth access-token lifetime.

### Changing a delegation

- **The application cannot widen its own delegation.** Managing connected apps is non-delegable, so no delegated credential can change any delegation.
- **The delegator may change their delegation at any time,** including an override wider than the consented default, within their own current RBAC and the profile cap. This happens through the authenticated management interface and is an explicit decision by the delegator, so it needs no new consent.
- **Editing a delegation and renewing consent are different events.** Editing: the delegator changes the delegation in the management interface. Renewing consent: the application sends a new authorization request, for example to obtain a widened profile, and the user approves it. Each is recorded as its own audit event, with its initiator; widenings are flagged, and the connected-apps page shows each connection's current delegation.
- **Profile changes follow the profile cap.**

### When the delegator loses access

Delegated credentials depend on their delegator at every request. Reduced RBAC rights constrain them at once, and when the delegator is disabled or deleted, all their delegated credentials stop working: Knox refuses tokens of inactive users (`validate_user`), the PR deletes a user's app tokens when the user is deactivated, and deleting a user deletes their tokens. An expired user is treated as disabled.

### Operations spanning several domains

**Every object an operation modifies must satisfy the rule of its own domain, and every object it only references must be readable.** Because delegations are enforced inside the central access functions, this follows wherever RBAC already checks a folder:

- **Moves.** When an object's folder changes, `BaseModelSerializer.validate_folder` checks `add` on the destination, on top of the `change` check on the object. A move therefore needs Update in the source domain and Create in the destination. With Update in Paris and only Read in Lyon, moving evidence from Paris to Lyon is refused.
- **Links between domains.** The object that changes needs the operation in its own domain; the object it points to only needs Read, which RBAC already requires to reference it.
- **Bulk operations** check every object they touch, not only the first domain.
- **Where RBAC itself does not check a destination,** the delegation inherits that gap (see Remaining risks).

### Domain overrides

- **Overrides are keyed by folder ID and shown as paths,** so they follow their folder when it is renamed or moved; deleting a folder deletes its override. An override on a folder the delegator cannot access has no effect.
- **The root folder cannot be an override:** the default plays that role, and the root folder's own objects, the shared reference data, follow the default.
- **Objects the delegation does not allow to read behave as if the user could not see them:** they are masked in reads like any unreadable related object, links to them are refused, and aggregates are computed without them, or the endpoint is refused if it cannot leave them out.
- **The focus header can only narrow.** It intersects with the delegation and never widens it, whether or not the `focus_mode` flag is on.
- **Focus-exempt paths that return domain data** are refused to a delegation that does not allow Read everywhere.

### Enforcement

- **Credential context.** A value in `core/context.py`, next to `focus_folder_id_var`, describing the authenticated credential: its kind and, when it has one, its delegation, resolved into one set of allowed folders per operation by walking the folder tree once (Knox for PATs, `OIDCServiceAccountAuthentication` for OAuth tokens and service accounts). Correctness comes first: the delegation is resolved on every request, and caching is added only if measurements require it, with version-based invalidation covering every input (the grant, the profile, the overrides and the folder tree). The delegator's RBAC is computed on every request in any case.
- **Fail closed.** A delegated credential (an MCP token, any credential with a delegation) is accepted only in the same step that sets its context. If the context cannot be built, the credential is refused.
- **Isolation between requests.** A middleware clears the context when a request begins, and never at the end: streaming responses, such as chat's (`chat/views.py`), run after the middleware has returned and still compute access (`chat/scoping.py`). This is sufficient for the way the backend runs. Gunicorn uses sync workers (`startup.sh` sets no threads and no other worker class), so a process handles one request at a time, and a streaming response finishes in the same thread before the next request starts. No backend code starts threads or asynchronous work inside a request. Any that is added must carry the context over (`contextvars.copy_context`).
- **Enforced worker model.** A gunicorn configuration file passed by `startup.sh` gets an `on_starting` hook that stops the server unless the worker class is `sync`. This also catches `GUNICORN_CMD_ARGS`, through which an option such as `--threads 4` would silently switch to the `gthread` worker. `gthread` probably keeps the same isolation, since each thread handles one request at a time, but it is allowed only once the isolation tests pass under it.
- **Central functions.** `RoleAssignment._get_grant_folder_set`, which backs `is_access_allowed`, `get_allowed_folder_ids` and `has_permission_anywhere`, maps the permission to its operation and plane, refuses control-plane and non-delegable permissions, and intersects the user's granted folders with the folders where the delegation allows that operation. The two early returns in `is_access_allowed` get the same check.
- **Registry, from step 1a.** Every permission and every endpoint outside RBAC is mapped to an operation and a plane. A test fails on any unclassified one. Until then, MCP v1 relies on a hand-written control-plane list, which only has to be right for the inventoried MCP operations.
- **Administrator endpoints.** `IsGlobalAdmin` refuses every delegated credential, since control-plane operations are never delegated.
- **Self-service endpoints.** A permission class refuses delegated credentials on the views that only require authentication: `auth-tokens/`, `auth-tokens/<pk>/`, `change-password/`, `revoke-sessions/`, Knox `logoutall/`, and writes to `connected-apps/` and `current-user/`.
- **Background tasks.** Access is decided in the request, before work is queued, and the request hands the task the explicit objects it may touch, already restricted by the delegation. A task runs without the credential context, so it never derives its working set, or decides access again, from the user alone.

### MCP v1 (first step)

MCP is the first consumer of this model. How it is served (the secretless `ca_mcp` sidecar, the dedicated MCP listener, the operation inventory, the MCP resource boundary and the proxy isolation) is decided in [mcp-app-access-model](mcp-app-access-model.md). From this ADR's point of view, v1:

- **Offers levels 0 and 1.** The MCP server enforces the connection's default selection; it cannot know which domain a call will touch, so overrides (level 2) arrive with step 1a, when the backend enforces delegations.
- **Applies the backstop in the backend.** Every MCP token is treated as a level-0 delegation: control-plane and non-delegable operations are refused, through the control-plane check, the `IsGlobalAdmin` refusal and the self-service permission class. From step 1a, the backend applies the grant's own delegation.
- **Accepts MCP tokens only on the MCP listener, for inventoried operations,** as decided in [mcp-app-access-model](mcp-app-access-model.md).
- **Leaves existing admin-registered OAuth clients unfiltered.**

### What each step guarantees

| Guarantee | MCP v1 | Step 1a |
|---|---|---|
| Control-plane operations, administrator endpoints and credential management refused to MCP tokens | backend | backend |
| MCP tokens validated by the backend as the MCP resource server (audience `<url>/mcp`), on inventoried operations only | backend | backend |
| The connection's default selection (levels 0 and 1) | MCP server, trusted | backend |
| Domain overrides (level 2) | not offered | backend |
| A changed or revoked delegation applies to the next request | MCP server, within about a minute | backend |
| Delegated PATs and service accounts | — | backend |
| Every operation classified, unclassified ones refused to delegated credentials | MCP operations, by the inventory | whole API, by the registry |

### Steps

| Step | Content | Effect on API clients |
|---|---|---|
| **MCP v1** | MCP v1 above, implemented as decided in [mcp-app-access-model](mcp-app-access-model.md), with levels 0 and 1 | Additive |
| **1a. Delegation** | Delegations on PATs, service accounts and app connections, with the migration setting `unfiltered` on existing ones; defaults and overrides; non-delegable actions refused to every delegated credential; the registry of operations and planes with its fail-closed test, so the classification is complete before any delegated PAT or service account exists; a control-plane audit category. The backend takes over the enforcement of delegations from the MCP server. Also fixes `FocusModeMiddleware` leaving the previous request's focus in place when the header is invalid | New optional fields |
| **2. Administrator policies** | Forbid unrestricted credentials, with exemptions for an external management system's account; maximum lifespan; make a delegation the API default; consent policies per app, for apps that identify themselves with CIMD | Opt-in |

Later, in its own ADR: step-up authentication for the control plane (protected actions), PIM-style activation of control-plane roles, deny assignments (for example, a domain no app may reach), and Conditional Access conditions.

Per-model precision, such as "only evidence", is out of scope. If it is ever needed, it can come back as an advanced option for PATs and service accounts, on the same structure.

### Deviations from Microsoft

The terms used here are mapped to Microsoft's in the appendix.


- **Delegated access to data is finer than Azure's resource manager.** Azure's resource manager has a single delegated permission, `user_impersonation`, which gives an app the user's full resource rights. Microsoft's fine-grained delegated permissions exist on Microsoft Graph (directory, mail, files). We apply the Graph practice to our data, because "an assistant that reads but does not change" is the main thing users ask for.
- **Overrides replace instead of adding up.** In Azure, role assignments only add up, and only deny assignments subtract. Here the most specific override wins, even when it is more restrictive than its parent, as with folder permissions on a file system. This is more intuitive for the person delegating, and safe, since RBAC still caps every rule.
- **Apps can register themselves.** Microsoft has no anonymous registration: a publisher registers its app. MCP clients rely on it, so dynamic client registration stays, behind the redirect-host allowlist, until clients move to CIMD.

## Security

**Conclusion: the design does not grant rights beyond RBAC and preserves existing behavior for unfiltered credentials.** It introduces new authorization mechanisms and corresponding implementation risks, addressed by the invariants and verification below. If enforcement fails for an unfiltered credential, that credential keeps today's behavior. If it fails for a delegated one, the credential is refused rather than widened. Browser sessions do not change at all.

### Security invariants and verification

Each invariant is a requirement on the implementation, followed by the tests required to validate it. Tests provide evidence, not proof: they cannot rule out a business operation that bypasses the central checks (see Remaining risks).

1. **A delegation only subtracts.** The delegator's RBAC, their delegation and, for an app connection, the organization's profile are three independent caps, each able only to refuse. The checks run in the same functions as RBAC, and there is no code path where a delegation or a profile allows anything.
   *Tests:* unchanged results for browser sessions and unfiltered credentials.
2. **Administration and credential management are out of reach.** Control-plane operations are never delegated; unclassified permissions count as control plane; every permission maps to one operation, and an unmapped custom permission is non-delegable; `IsGlobalAdmin` and the self-service permission class refuse every delegated credential. A delegated credential therefore cannot create a stronger one, which closes the escalation path from an app token to a long-lived full-rights PAT.
   *Tests:* refusals on control-plane operations, administrator endpoints and every non-delegable view; the operation mapping, with unmapped custom permissions refused; from step 1a, the registry test failing on any unclassified permission or endpoint.
3. **Rules resolve predictably.** The nearest override wins, an empty selection denies, an absent override inherits, the root folder follows the default, level 0 is the four operations together, and levels are never stored. For an app connection, the profile cap applies to every rule; a profile change may restore rights an owner explicitly chose, never authorize rights they have not chosen.
   *Tests:* on the example above, read everywhere, create in Paris but not in Paris / Finance, update in Lyon; an empty selection denying and an absent override inheriting; an override allowing create refused when the profile only allows read; a profile tightened applying to existing connections, then restored giving back only the rights their owners had chosen, and widened beyond those choices leaving them unchanged; a permission added later and classified as data plane joining its operation, subject to RBAC, while an unclassified one stays out.
4. **Only the `unfiltered` flag means no delegation.** It is non-null and defaults to false; a missing, empty or malformed delegation allows nothing, or the credential is refused. No form preselects unrestricted access, and existing credentials stay unfiltered until an administrator sets a delegation.
   *Tests:* the stored states: the flag defaulting to false, level 0 excluding control-plane operations, an empty default allowing nothing, a malformed delegation refused.
5. **Inputs come from the server, and failures refuse.** The credential context comes only from the authenticated credential, never from request input; headers can only narrow. A delegated credential is accepted only together with its context. From step 1a, the backend resolves the current grant and profile on every request, and no permission set is captured when a token is issued; a cached delegation, if caching is ever added, is invalidated by any change to its inputs.
   *Tests:* refusal when a delegated credential's context cannot be built; from step 1a, a delegation changed between two requests applying to the second one; a focus header narrowing but never widening.
6. **Requests are isolated.** The context is cleared at the start of every request, never at the end; gunicorn refuses to start with any worker class other than `sync`; work started inside a request on another thread, or asynchronously, carries the context over (`contextvars.copy_context`); background tasks receive their objects from the request and never decide access again from the user alone.
   *Tests:* two requests in a row on the same worker with different credentials; a streaming response that keeps its context to the end; gunicorn refusing to start with another worker class.
7. **Every affected object satisfies the rule of its own domain.** Each object an operation modifies needs the operation in its domain, each object it references must be readable, and bulk operations check every object they touch. Objects the delegation does not allow to read behave as invisible.
   *Tests:* with Update in Paris and Read in Lyon, a move from Paris to Lyon refused; a link from a Paris object to a readable Lyon object allowed; a bulk update across domains refused as soon as one object falls outside the delegation; a cross-domain test for every operation the MCP inventory flags; unreadable objects masked in reads, refused as link targets and left out of aggregates.
8. **Only the delegator changes a delegation, visibly.** The application cannot widen its own delegation; every change is audited, widenings flagged, with editing and consent renewal as distinct events. When the delegator is disabled, expired or deleted, every delegated credential stops working.
   *Tests:* an app token refused when it tries to change a delegation; every change recorded with its initiator; the delegator disabled, expired or deleted, then every delegated credential refused at the next request.
9. **MCP meets the guarantees of [mcp-app-access-model](mcp-app-access-model.md):** MCP tokens are valid only at the MCP resource, on inventoried operations classified by their actual effects, and browsers never hand session cookies to the MCP server.
   *Verification:* as listed in that ADR.

10. **A compromised MCP server stays bounded.** The backstop refuses control-plane operations, administrator endpoints and non-delegable actions to MCP tokens, on operations that are all inventoried. A compromise gives the data-plane rights of the users whose tokens pass through it, until those tokens expire: it cannot create users, change emails, mint PATs or alter settings. Revoking a connection takes effect at once.
    *Tests:* covered by invariant 2 and by [mcp-app-access-model](mcp-app-access-model.md).
11. **New endpoints are classified.** Any endpoint that does not go through the central functions declares its plane. Until step 1a, control-plane endpoints are added to the backstop by hand.
    *Tests:* the registry test of invariant 2.

### Remaining risks, accepted as low

- **MCP v1 trusts the MCP server for the connection's default selection.** A compromise gives an app the full data-plane rights of its user on the inventoried operations, whatever its selection, until the token expires. A misclassified tool cannot cause this, since a test measures each operation's effects. Step 1a moves enforcement to the backend (see What each step guarantees). A shorter access-token lifetime reduces the window meanwhile.
- **A coarse selection gives more than intended.** Allowing create, for instance, allows creating any kind of data-plane object the delegator can create. Delegations never reach the control plane or credential management, and overrides narrow them where it matters.
- **MCP v1's control-plane list is hand-written.** It only has to be right for the inventoried operations, each reviewed with its effects. Step 1a replaces it with the registry and its fail-closed test, before any delegated PAT or service account exists.
- **Code that writes without checking a permission bypasses delegation,** as it already bypasses RBAC. The same holds for an operation that checks only some of the objects or domains it touches, such as a bulk endpoint checking only the first object, or a move that does not check its destination. The effect tests of the MCP inventory and the registry of step 1a reduce it.
- **Unfiltered credentials keep today's power,** including creating PATs. This is deliberate, to avoid breaking external management systems. Administrators narrow them with step 2's policies.

### What would change this assessment

Breaking any invariant above requires a new decision. In particular: letting a delegation grant access or reach control-plane operations, letting any delegation pass a non-delegable action, delegating an unmapped custom permission, letting a shared profile give a connection rights its owner has not chosen, letting an application widen its own delegation, letting an override exceed the profile, keeping delegated credentials usable after their delegator is disabled or deleted, caching a delegation without invalidating it on every input change, reading a missing or empty delegation as unfiltered, capturing permissions at token issuance, reading the credential context from request input, accepting a delegated credential without its context, clearing the context at the end of requests, changing the concurrency model (worker class, threads, ASGI, work on other threads) without a security review, preselecting unrestricted access in a form, or weakening the MCP guarantees decided in [mcp-app-access-model](mcp-app-access-model.md). A concurrency change needs that review even with `contextvars.copy_context`, which carries the context over but does not manage its lifetime.

## Appendix: Microsoft vocabulary

| Microsoft term | Here |
|---|---|
| Delegated permissions, granted by consent | The delegation of an app connection or a PAT, which acts on its user's behalf |
| Application permissions | A service account's own role assignments, optionally narrowed by a delegation |
| `DataActions` / `Actions` in a role definition | Data-plane and control-plane permissions. Only data-plane permissions can be delegated |
| `user_impersonation` (full delegated access) | The `unfiltered` flag, shown as **Unrestricted (including administration)**. Distinct from level 0, shown as **All data**, which never includes administration |
| Admin consent | Not needed: control-plane operations are never delegated |
| App consent policy | The presets administrators offer on the consent page |
| Scope (where a role assignment applies) | **Domain override**: a folder subtree with its own selection. We avoid "scope" because OAuth calls permission strings "scopes" |
| Control plane / data plane | The classification of permissions in Operations and planes |
| — | **Non-delegable actions**: credential management, which no delegation ever covers |
| Protected actions, PIM, Conditional Access, deny assignments | A later ADR |
| Restrict full-scoped tokens, maximum lifespan (Azure DevOps PAT policies) | The administrator policies of step 2 |
