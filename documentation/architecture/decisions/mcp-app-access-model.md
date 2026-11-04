# Let users connect AI apps over OAuth, narrowed by built-in profiles of independent actions

- Status: Accepted
- Deciders: @tchoumi313

## Context

Customers want to plug AI apps (Claude Code, Copilot Studio, MCP Inspector, and others) into CISO Assistant through MCP. Until now, each user had to run the MCP server themselves: clone the repository, install Python and `uv`, and start `ca_mcp` on their own machine over stdio, with a personal access token (PAT) in its environment. Cloud apps such as Copilot Studio cannot start a local process, so someone also had to host `ca_mcp` as an HTTP server, expose it on the internet and keep it running. In both cases the app had all the user's rights through the PAT, with no consent, no expiry policy, and no way for an administrator to see or cut it.

The instance should serve MCP itself, at `<url>/mcp`, so that a user only enters a URL in their app and signs in.

MCP clients expect OAuth 2.1: they discover the server (RFC 9728, RFC 8414), register themselves (RFC 7591, DCR), and send the user through a browser sign-in with PKCE. Most of them cannot be registered in advance, because they create a new client at each install. Copilot Studio even creates one per connection, and does not send the `resource` parameter (RFC 8707).

Administrators asked for three things first: an off switch, a say on who may connect, and a list of every connection. Then they asked that an app can get less than its user. The first version of that used cumulative levels (read, create, update, approve). It was rejected: an approver should not be able to create or delete just because approve sits higher. The user should pick the combination they want.

## Decision

We will run MCP as its own service, `backend-mcp`, acting as an OAuth resource server, with allauth's IdP as the authorization server at `<url>/api`. Users connect an app themselves, on a consent page, if an administrator allowed them. On that page they pick one of four built-in profiles. Each profile is a combination of independent actions: read (always), create, and update (which includes delete). Every tool call runs in-process as the user, so the app never gets more than the user, and the profile narrows it further.

## Consequences

### Architecture (built)

- `backend-mcp` is a separate process. It shares the backend's database, checks each token there, and dispatches tool calls in-process as the user. The token is never passed through to `/api`.
- allauth is the authorization server, with issuer `<url>/api`. The authorize view also accepts the Knox cookie of a user already signed in to the frontend. Nowhere else does the Knox cookie count as a session.
- Clients register through DCR only. Self-registered clients can call `/mcp` only: their tokens are refused on `/api`.
- The `resource` parameter is optional, because Copilot Studio does not send it. When it is missing, the token is bound to the MCP resource anyway.

### Who may connect (built)

- A connection that is not used for 30 days ends: its refresh token expires and the user must approve the app again (`OAUTH_REFRESH_TOKEN_IDLE_DAYS`, `0` = never). allauth issues a new refresh token at each refresh, so an app in use never notices.
- The `mcp` feature flag is the kill switch. Off: every connection is blocked, but kept, and works again when it is turned back on.
- `can_connect_apps` on the user is off by default and only an administrator can change it. Unticking it, or deactivating the user, revokes all their connections at once.
- Administrators see every connection in **Organization > Connected apps**, with its redirect hosts and allowed actions, and can search by user or app. They can revoke one, or revoke an app for everyone. Revoking an app for everyone groups the registrations that share a name and a return address, and deletes self-registered clients so their IDs cannot be reused.

### What an app may do (built)

- There are three actions. Read covers `get_*`, `list_*`, `count_*` and `find_*`. Create covers `create_*` and `import_*`. Update covers `update_*`, `sync_*`, `refresh_*` and `delete_*`. Read is always granted, because the other tools need IDs that only read tools return.
- Each tool's action is declared in a list in `ca_mcp/server.py`, never guessed from its name. A test fails when a tool has no action. A new tool must be added to one of the lists.
- There are four built-in profiles, one per combination: Read only (the default), Read and create, Read and update, and Read, create and update. They are not exposed: there is no API and no admin screen, and nobody can edit them. The model keeps `can_create`, `can_update` and `builtin`, so that custom profiles can come later without a new data model.
- The user picks a profile on the consent page. A client that skips consent gets the default profile.
- The choice is stored as a grant per user and client, not on the token, because allauth issues new tokens at each refresh and copies nothing across. No grant means no access. There is no fallback.
- To give an app more, the user approves it again and picks another profile. Profiles cannot be widened behind the user's back, because nobody can edit them.
- `tools/list` hides the tools whose action is not granted. A guard on each write tool is the actual boundary. The `get_my_access` tool tells the agent what it can and cannot do. We do not use step-up (`insufficient_scope`) for now.
- MCP has a single scope, `mcp:read`, which means "may use MCP". Every MCP token gets it, whatever the profile, and `backend-mcp` requires it. What the app may do comes only from the profile.

### Audit and limits (built)

- Audit entries for changes made through an app keep the user as the actor and add `via_app` (client ID, name, profile). SIEM events carry it as `actor.app_name` and `actor.app_uid` in OCSF, and as `via_app` in the raw format.
- Every tool call, reads included, is logged by `backend-mcp` as `mcp tool call`, with the user, app, profile, actions, tool, outcome, duration and answer size.
- Each connection (one user with one app) has a budget: 60 calls per minute (`MCP_MAX_CALLS_PER_MINUTE`) and 2,000,000 characters per hour (`MCP_MAX_RESPONSE_CHARS_PER_HOUR`). `0` turns a limit off. An agent can loop, or be steered by a prompt injection into reading everything the user can see. The budget stops it from overloading the instance or pulling out the whole database in a few minutes, while normal use stays far below it.
- The counters live in the Django cache, so they are only exact when the cache is shared by all workers. The shared cache (memcached) is a separate piece of work.

### Next, in this order (decided, not built)

1. **Small hardening batch.** PKCE is required for confidential clients too. `dispatch` checks the HTTP method against the profile as a second guard: a read-only connection may only send `GET` and `HEAD`. Which methods create and update need is checked tool by tool before this is turned on.
2. **Apps as a governance list** ("Add an app"). See the next section.
3. **Domain limit.** A profile can be limited to some domains (with subdomains). In the Global domain, the app can still read catalog objects (frameworks, reference controls, threats, matrices, libraries), but not real controls, assets or audits. The request shape follows RFC 9396 (rich authorization requests). This lives in the core rights code, not in MCP, so it is its own project.

### Apps as a governance list (decided, not built)

- An administrator registers an app with its own client ID. Apps come in two kinds:
  - **Server apps** are confidential clients with an HTTPS redirect (Copilot Studio, a hosted agent). They can be marked **Trusted**.
  - **Desktop apps** use a loopback redirect (Claude Code, MCP Inspector). They can only be **Allowed**, never Trusted, because any program on the machine can listen on localhost and pretend to be them (RFC 8252, section 8.6). A desktop app never skips consent and never gets `/api`.
- Admin-registered apps are MCP only by default. An "Allow REST API access" tick opens `/api` for server apps.
- The profiles an app may offer are chosen on the app. Self-registered apps get all profiles.
- Skip consent is allowed only for trusted server apps.
- A deny list on redirect hosts blocks self-registration from those hosts and revokes their connections at once.
- CIMD (client ID metadata documents) replaces or complements DCR once enough clients support it. Check client support before building it.
- Self-registered clients that were never used, or not used for a long time, are cleaned up.

### Later (held, no date)

- Custom profiles, with checkboxes for create and update. The built-in ones are shown read-only.
- Profiles per user or user group: one more field on the profile and one more check when listing them.
- Profiles per app, which comes with the governance list above.
- An Approve action, when the first workflow tool (risk acceptance, commitment, assignment) is added. It is a separate action, not above Update.
- A PAT policy: a setting "PATs allowed on MCP", then deprecating them there.
- Making `resource` required, once Copilot Studio sends it.
- A per-user budget on top of the per-connection one, so that many apps cannot add up.
- A recommendation to set `OAUTH_DCR_ALLOWED_REDIRECT_HOSTS` in production.

## Security considerations

- An app can never do more than its user, because calls run in-process with the user's own permission checks. The profile only removes access. This is why there is no Administer action: changing a user's email, a team or a domain already needs the user's own right to do so.
- DCR is open: anyone can register a client. It gets nothing until a user who may connect apps approves it on the consent page. The warning on that page and the redirect list are the user's protection. `OAUTH_DCR_ALLOWED_REDIRECT_HOSTS` narrows it, and the deny list will narrow it further.
- The name of a self-registered app is chosen by the app and proves nothing. The UI shows each app's redirect hosts, which are the only reliable sign. Today every app is self-registered, so the UI has no badge to tell them apart. An "Added by an admin" badge comes back with admin app registration.
- Loopback redirects cannot prove which program is listening. Desktop apps are therefore never trusted, even when an administrator registers them. A trusted "localhost" entry would trust every local program.
- Risks we accept for now:
  - PATs bypass profiles;
  - delete is part of update;
  - the method guard is not there yet, so the tool guard is the only boundary in `backend-mcp`.
- Self-registered tokens are refused on `/api`, so a stolen MCP token cannot reach the REST API.
- Every call is logged and changes are tagged with the app, so an incident can be traced to one connection and revoked there.

## Alternatives considered

- **Cumulative levels (read < create < update < approve).** Rejected: a higher level forced the lower ones on, so an approver could also create and delete.
- **Free checkboxes on the consent page, with no profiles.** Rejected in favour of named built-in profiles, which give a stable name in logs and audit and leave room for admin-managed profiles later.
- **Admin-editable profiles now.** Postponed: not needed on day one, and editable profiles raise the question of widening a profile behind the user's back.
- **A separate Delete action.** Rejected: an app that can update can already empty an object.
- **Approve and Administer actions now.** Rejected: no tool approves anything yet, and administration is already limited by the user's rights. An empty action would look like protection without being one.
- **Profiles per app now.** Postponed: self-registered apps cannot be named in advance or told apart (every Copilot Studio agent shares `global.consent.azure-apim.net`), and there is no admin registration yet.
- **One scope per action (`mcp:write`, or `mcp:create` and `mcp:update`).** Rejected for now: the grant on the server already decides, so nothing would read these scopes. They only matter for step-up or for a client that shows what it was granted. A first version had `mcp:write`; it was removed before release.
- **Step-up with `insufficient_scope`.** Postponed: client support is uneven. Hiding tools and `get_my_access` work with every client.
- **Storing the profile on the token.** Rejected: allauth issues new tokens at refresh and copies no data, so the grant would be lost.
- **Proxying MCP calls to `/api` with the user's token.** Rejected: token passthrough would put the OAuth token on the REST API and is forbidden by the MCP spec. In-process dispatch keeps one permission path.
- **MCP inside the main backend process.** Rejected: a separate process can be scaled, turned off and exposed on its own.
- **CIMD now.** Postponed until enough clients support it. DCR works with all of them today.
