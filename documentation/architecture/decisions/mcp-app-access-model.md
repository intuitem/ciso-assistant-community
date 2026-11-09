# Serve MCP from the instance through a secretless sidecar, with OAuth consent and delegated access

- Status: Proposed (revises the first, in-process version of this decision)
- Date: 2026-11-09
- Deciders: @tchoumi313, @eric-intuitem
- Related: [delegated-permissions-over-rbac](delegated-permissions-over-rbac.md) (the authorization model this ADR implements for MCP: delegations, planes, the profile cap and the security invariants), [service-accounts-composition](service-accounts-composition.md)

## Context

Customers want to plug AI apps (Claude Code, Copilot Studio, MCP Inspector, and others) into CISO Assistant through MCP. Until now, each user had to run the MCP server themselves: clone the repository, install Python and `uv`, and start `ca_mcp` on their own machine over stdio, with a personal access token (PAT) in its environment. Cloud apps such as Copilot Studio cannot start a local process, so someone also had to host `ca_mcp` as an HTTP server, expose it on the internet and keep it running. In both cases the app had all the user's rights through the PAT, with no consent, no expiry policy, and no way for an administrator to see or cut it.

The instance should serve MCP itself, at `<url>/mcp`, so that a user only enters a URL in their app and signs in.

MCP clients expect OAuth 2.1: they discover the server (RFC 9728, RFC 8414), register themselves (RFC 7591, DCR, or Client ID Metadata Documents), and send the user through a browser sign-in with PKCE. Most of them cannot be registered in advance, because they create a new client at each install. Copilot Studio even creates one per connection, and does not send the `resource` parameter (RFC 8707).

An MCP server handles many users' tokens and faces the network, so it is the component most likely to be compromised. The first version of this decision ran tool calls in-process in a `backend-mcp` service, which held the database credentials and the Django secret key: a compromise would have exposed everything. What a connection may do, and how the backend enforces it, is decided in [delegated-permissions-over-rbac](delegated-permissions-over-rbac.md). This ADR decides how MCP is served and how it plugs into that model.

## Decision

We will serve MCP at `<url>/mcp` from a sidecar running `ca_mcp`, the same code as in stdio mode. The sidecar holds no database access and no secret other than an introspection credential. It turns MCP requests into standard API calls, carrying the caller's OAuth token, to a dedicated backend listener that acts as the resource server for `<url>/mcp` and serves only the operations the tools use. allauth's IdP is the authorization server at `<url>/api`. Users connect an app themselves, on a consent page, if an administrator allowed them, and choose a delegation preset. What the connection may then do follows [delegated-permissions-over-rbac](delegated-permissions-over-rbac.md): **RBAC ∩ delegation ∩ profile**, with control-plane and non-delegable operations always refused. Version 1 offers levels 0 and 1, enforced by the MCP server, with a backend backstop; domain overrides come with that ADR's step 1a.

## Consequences

### Architecture

- **The MCP server is `ca_mcp`, run as a sidecar from the community `mcp` image.** In each customer's pod it runs next to the backend, under its own user ID, with no access to the backend's database volume, environment or secrets. It passes the caller's OAuth token through to the backend; the backend does not speak MCP.
- **It learns each token's delegation through allauth's token introspection,** with `populate_introspection_response` adding the grant's selection and `is_introspection_allowed` limited to the sidecar's client. Introspection requires `IDP_OIDC_INTROSPECTION_ENABLED` and gives the sidecar its only secret: client credentials that let it check tokens it already holds, and nothing else. allauth limits introspection to 60 requests a minute per client, so the sidecar caches each answer for about a minute. Revocation still takes effect at once, because the backend checks the token itself on every call.
- **MCP tokens are accepted only on a dedicated MCP listener:** a second gunicorn bind, turned on by an environment variable, bound to `127.0.0.1` in a pod and an internal port the reverse proxy does not route in compose. Every other listener refuses them.
- **The MCP listener serves only the operations the tools use.** An inventory kept next to the tools lists each operation the `ca_mcp` tools perform (about 108 route patterns across 126 tools): route, method, custom action and any parameter that changes the effect. Each entry records the permissions the operation actually checks, their CRUD operation, and all its effects: database writes, emails, queued tasks, and outbound calls such as ITSM synchronization and webhooks. A bulk operation is classified by its strongest effect. The inventory flags every operation that can touch several domains or objects, directly or indirectly. Every other operation is refused on the MCP listener, so the API reachable through MCP is a finite, reviewed list, whatever the sidecar sends.
- **allauth is the authorization server, with issuer `<url>/api`.** The authorize view also accepts the Knox cookie of a user already signed in to the frontend; nowhere else does the Knox cookie count as a session. The backend serves the authorization-server metadata; the sidecar serves only `/mcp` and the protected-resource metadata.
- **The reverse proxy isolates `/mcp`** on the app's host. On every route to the sidecar (`/mcp`, `/.well-known/oauth-protected-resource`) it removes the `Cookie` request header, removes `Set-Cookie` and `Service-Worker-Allowed` from responses, and adds `Content-Security-Policy: sandbox` and `X-Content-Type-Options: nosniff`. The compose Caddy configuration does this by default, and the README documents it for other proxies.
- **Removed from the first version:** the in-process `backend-mcp` service (`backend/mcp_server/`) and `Dockerfile.mcp`.

### The MCP resource boundary

The MCP specification forbids an MCP server from passing a client's token on to an API the token was not issued for, and from accepting tokens that were not issued for it. The sidecar forwards the caller's token to the backend, so the boundary of the protected resource has to be explicit:

- **One resource, two components.** The protected resource `<url>/mcp` is implemented by two components deployed together: the protocol front, which is the sidecar, and the execution endpoint, which is the backend's MCP listener. It is the same resource that the first version of this decision ran in a single process. Moving execution out of the network-facing process keeps secrets out of it without creating a new resource.
- **The execution endpoint is the resource server.** The MCP listener validates every token itself, without relying on the front's check: active, issued by this instance, audience `<url>/mcp`, and a live `AppGrant`. Only then does it run an operation from the inventory.
- **Every MCP token carries that audience.** Clients send it as a resource indicator (RFC 8707). When a client omits it, as Copilot Studio does, the authorization server records `<url>/mcp` on the grant itself, so the audience check is the same for every client. allauth carries a grant's resource from the authorization request to the code and then to the token, so the authorize view can set it.
- **The listener is not a downstream resource.** It exposes no API of its own, only the inventoried operations of the MCP resource, and it refuses any token with another audience. The API listeners, in turn, refuse tokens whose audience is `<url>/mcp`. The front presents the token to nothing else; introspection goes to the authorization server.
- **The reasons behind the specification's rule are covered.** Controls cannot be bypassed, because the token works nowhere else. Every action is attributed to the app (`via_app`). The backend does not rely on the front's validation.
- **Accepted interpretation.** The MCP specification does not say explicitly whether an MCP server may be split into a protocol front and an execution endpoint that share one audience. Clients and the authorization server see a single resource at `<url>/mcp`, so the split cannot be observed from outside. We accept the reading above (decided by @eric-intuitem, 2026-11-08).
- **Fallback.** If a later revision of the specification rules this out, the front exchanges the MCP token for an internal credential (token exchange, RFC 8693). allauth does not implement token exchange, so this would mean a custom grant, a client secret in the front, and a second token carrying the same delegation.

### Who may connect

- **Clients register through DCR,** and through Client ID Metadata Documents where they support it. Self-registered clients get nothing until a user who may connect apps approves them on the consent page.
- **A connection that is not used for 30 days ends:** its refresh token expires and the user must approve the app again (`OAUTH_REFRESH_TOKEN_IDLE_DAYS`, `0` = never). allauth issues a new refresh token at each refresh, so an app in use never notices.
- **The `mcp` feature flag turns MCP on or off for the instance.** Off: every OAuth app connection is blocked, but kept, and works again when it is turned back on. It does not affect `ca_mcp` run by a user over stdio with their own PAT.
- **`can_connect_apps` on the user** is off by default and only an administrator can change it. Unticking it, or deactivating the user, revokes all their connections at once.
- **Administrators see every connection** in **Organization > Connected apps**, with its redirect hosts and current delegation, and can search by user or app. They can revoke one, or revoke an app for everyone. Revoking an app for everyone groups the registrations that share a name and a return address, and deletes self-registered clients so their IDs cannot be reused.

### What an app may do

- **The user picks a delegation preset on the consent page:** All data (level 0), Read, Read and create, Read, create and update, or Read, create, update and delete. A client that skips consent gets the default profile. Domain overrides (level 2) are edited afterwards on the connection, from step 1a of [delegated-permissions-over-rbac](delegated-permissions-over-rbac.md).
- **The choice is stored as a grant per user and client (`AppGrant`), not on the token,** because allauth issues new tokens at each refresh and copies nothing across. The grant stores the default consented to; its `ConnectionProfile` provides the organization's cap. No grant means no access; there is no fallback.
- **Each tool's operations come from the inventory,** never guessed from its name. A test fails when a tool has no entry, so a new tool must be added to the inventory.
- **In v1, the sidecar enforces the connection's default selection,** which we trust because we maintain its code. A tool is allowed when every operation it performs is in the selection; unknown tools are refused. The sidecar cannot know which domain a call will touch, so v1 offers levels 0 and 1 only.
- **The backend backstop applies from v1:** the backend treats every MCP token as a level-0 delegation, refusing control-plane and non-delegable operations. Tools that write to the control plane (`update_user`, `create_folder`) are refused. From step 1a, the backend applies the grant's own delegation.
- **`tools/list` hides the tools the delegation does not allow,** and the `get_my_access` tool tells the agent what it can and cannot do. We do not use step-up (`insufficient_scope`) for now.
- **MCP has a single scope, `mcp:read`,** which means "may use MCP". Every MCP token gets it, and the MCP listener requires it. What the app may do comes only from the delegation.
- **Existing admin-registered OAuth clients keep today's behavior,** unfiltered.

### Audit and limits

- **Audit entries for changes made through an app keep the user as the actor and add `via_app`** (client ID, name, delegation). SIEM events carry it as `actor.app_name` and `actor.app_uid` in OCSF, and as `via_app` in the raw format.
- **Every tool call, reads included, is logged by the sidecar** as `mcp tool call`, with the user, app, delegation, tool, outcome, duration and answer size.
- **Each connection (one user with one app) has a budget,** enforced by the sidecar: 60 calls per minute (`MCP_MAX_CALLS_PER_MINUTE`) and 2,000,000 characters per hour (`MCP_MAX_RESPONSE_CHARS_PER_HOUR`); `0` turns a limit off. The budget stops a looping or prompt-injected agent from overloading the instance. It is a safeguard for well-behaved deployments, not a security boundary: a compromised sidecar would ignore it.

### Next and later

- **PKCE required for confidential clients too.**
- **Apps as a governance list.** An administrator registers an app with its own client ID. Server apps (confidential clients with an HTTPS redirect) can be marked Trusted; desktop apps (loopback redirect) can only be Allowed, never Trusted, because any program on the machine can listen on localhost and pretend to be them (RFC 8252, section 8.6). Skip consent is allowed only for trusted server apps. A deny list on redirect hosts blocks self-registration from those hosts and revokes their connections. Self-registered clients that were never used, or not used for a long time, are cleaned up. Consent policies per app follow step 2 of [delegated-permissions-over-rbac](delegated-permissions-over-rbac.md).
- **Making `resource` required,** once Copilot Studio sends it.
- **A per-user budget** on top of the per-connection one, so that many apps cannot add up.
- **Workflow tools** (risk acceptance, commitment, assignment): their custom permissions are mapped in the registry of [delegated-permissions-over-rbac](delegated-permissions-over-rbac.md), or kept non-delegable.

## Security

**Conclusion: serving MCP this way adds no path to more than a connection's delegation, and a compromise of the network-facing component stays bounded.** The sidecar holds no secrets that open the database or the instance; every authorization decision is made by the backend, under the invariants of [delegated-permissions-over-rbac](delegated-permissions-over-rbac.md).

### Why the sidecar cannot be turned into more access

1. **It holds nothing worth stealing beyond the tokens it sees.** No database access, no Django secret key, no IdP signing key; its only secret lets it introspect tokens it already holds.
2. **MCP tokens are only valid at the MCP resource.** The backend's MCP listener validates each token's audience itself, every MCP token carries `<url>/mcp` as its audience, and the API listeners refuse such tokens. The listener serves only inventoried operations and is not reachable from outside the pod or the compose network. The token is never accepted by an API it was not issued for, and an app cannot skip the MCP server.
3. **A compromised sidecar stays bounded.** The backstop refuses control-plane operations, administrator endpoints and non-delegable actions to MCP tokens, on operations that are all inventoried. A compromise gives the data-plane rights of the users whose tokens pass through it, until those tokens expire: it cannot create users, change emails, mint PATs or alter settings. Revoking a connection takes effect at once.
4. **Browsers never hand session cookies to the sidecar.** The reverse proxy removes them on the MCP routes, and its responses cannot run script as the app or set cookies on the app's host.
5. **Consent stays with users who may connect apps.** DCR is open, but a registered client gets nothing until such a user approves it. The consent page shows each app's redirect hosts, the only reliable sign of who it is, since a self-registered app chooses its own name. Loopback redirects cannot prove which program is listening, so desktop apps are never trusted.
6. **Every change is attributed.** Audit entries carry `via_app`, and every tool call is logged, so an incident can be traced to one connection and revoked there.

### Verification

Tests provide evidence, not proof; they are required validation for this design:

- every read operation in the inventory producing no database write, email, queued task or outbound call, and every write operation producing only the effects its entry declares; HTTP methods are not trusted to describe effects (`GET /api/loaded-libraries/{id}/update/` writes);
- the tools' calls checked against the inventory, and a tool without an entry failing the test;
- every inventoried operation called with an MCP token; MCP tokens refused on the API listeners and on operations outside the inventory; tokens with another audience refused on the MCP listener;
- a cross-domain test for every operation the inventory flags;
- control-plane tools refused to MCP tokens from v1;
- the compose proxy configuration applying the isolation rules.

### Remaining risks, accepted as low

- **In v1, the sidecar is trusted for the connection's default selection.** A compromise gives an app the full data-plane rights of its user on the inventoried operations, whatever its selection, until the token expires. A misclassified tool cannot cause this, since a test measures each operation's effects. Step 1a of [delegated-permissions-over-rbac](delegated-permissions-over-rbac.md) moves enforcement to the backend. A shorter access-token lifetime reduces the window meanwhile.
- **Our reading of the MCP specification.** Forwarding the token rests on the resource boundary above. A reviewer, or a future revision of the specification, could read the rule more strictly; token exchange remains the fallback.
- **A self-registered app can trick a user into consenting.** It then gets that user's data within the consented selection, since its token only works through the MCP server, and never the control plane. Setting `OAUTH_DCR_ALLOWED_REDIRECT_HOSTS` to the AI clients an instance supports limits which apps can register at all.
- **A deployment without the proxy rules for `/mcp`.** Browsers could then send session cookies to the sidecar, and its responses would run on the app's origin. The compose configuration applies the rules by default, and the README states them for other proxies.
- **v1's control-plane list is hand-written.** It only has to be right for the inventoried operations, each reviewed with its effects. Step 1a replaces it with the registry and its fail-closed test.

### What would change this assessment

Giving the sidecar database access or a backend secret, accepting MCP tokens outside the MCP listener or with another audience, presenting them to any other resource, serving operations outside the inventory on the MCP listener, removing the backstop, or dropping the proxy isolation rules from the default configuration would reopen these questions and requires a new decision.
