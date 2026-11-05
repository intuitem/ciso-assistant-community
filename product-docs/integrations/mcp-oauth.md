---
description: >-
  Let AI assistants such as Copilot Studio or Claude Code connect to CISO
  Assistant with each user's own login, without copying a Personal Access Token.
---

# MCP sign-in with OAuth

Compatible with: SaaS or on-premises, CE or Pro

Tested MCP clients: Microsoft Copilot Studio, Claude Code, MCP Inspector

With OAuth sign-in, a user adds the CISO Assistant MCP URL to their AI assistant
and signs in with their normal CISO Assistant account. They don't need to create
or paste a Personal Access Token (PAT).

- **Each user approves the app themselves**, on a consent page in CISO Assistant.
- **The app gets that user's permissions.** It sees the same domains and objects
  as the user in the UI, no more.
- **The app can get less than the user.** When they approve, the user picks a
  profile, for example "Read only".
- **The user can revoke the app at any time** from their profile settings.

This page covers the OAuth setup. For the MCP server itself, the tools and the
stdio setup, see the [MCP setup guide](mcp.md).

### How it works

1. The user gives the MCP URL to their client: the instance URL followed by
   `/mcp`, for example `https://<your-instance>/mcp`.
2. The client calls the URL without a token. The server answers `401` and tells
   the client where to sign in.
3. The client registers itself with CISO Assistant. This step is called Dynamic
   Client Registration (DCR).
4. A browser opens on the CISO Assistant login page. The user signs in as usual,
   including MFA or SSO.
5. CISO Assistant shows a consent page. The user picks a profile and clicks
   **Authorize**.
6. The client gets a token and uses it for every MCP call, until the user
   revokes it.

<figure><img src="../.gitbook/assets/mcp-oauth-login.png" alt=""><figcaption><p>Step 4: the usual CISO Assistant login page. A user who is already signed in skips it</p></figcaption></figure>

<figure><img src="../.gitbook/assets/mcp-oauth-consent.png" alt=""><figcaption><p>Step 5: the consent page for Claude Code. The yellow box warns that the user is adding a new app nobody checked, and shows where it sends the user back. The user picks a profile; Read only is preselected</p></figcaption></figure>

The MCP server runs as its own service, `backend-mcp`, next to the backend. It
shares the backend's database and checks each token there. Tool calls run inside
CISO Assistant as the signed-in user, with the same permission checks as the UI.

### Profiles

A profile says what an app may do once connected. An app can always read. On
top of that, it may create data, update data (which includes deleting), both,
or neither. There is one built-in profile for each choice:

| Profile                 | Read | Create | Update and delete |
| ----------------------- | ---- | ------ | ----------------- |
| Read only (the default) | yes  | no     | no                |
| Read and create         | yes  | yes    | no                |
| Read and update         | yes  | no     | yes               |
| Read, create and update | yes  | yes    | yes               |

- On the consent page, the user picks one of the profiles. **Read only** is
  preselected.
- A profile only removes access. A user who can't edit a folder in the UI can't
  edit it through MCP either, whatever the profile.
- Apps that skip the consent page get **Read only**.
- The app only sees the tools its profile allows. It can call `get_my_access`
  to learn what it may do.
- To give an app more, the user connects it again and picks another profile.

The profiles are built in and can't be changed for now. Every profile is
offered to every app.

If the server runs read-only (`CA_MCP_READ_ONLY=true`), the write tools are
hidden whatever the profile.

### Enable it (administrators)

{% stepper %}
{% step %}

#### Start the MCP service

The service is off by default. For now it ships in `docker-compose-build.yml`
only, built from source. Start it with the `mcp` profile:

```bash
docker compose -f docker-compose-build.yml --profile mcp up -d --build
```

The proxy sends these paths to `backend-mcp`, so it is served on your existing
certificate:

- `/mcp`
- `/.well-known/oauth-protected-resource/mcp`
- `/.well-known/oauth-authorization-server/api`

If you run your own reverse proxy, add these three routes. Everything else stays
as before.
{% endstep %}

{% step %}

#### Set the public URL

`CISO_ASSISTANT_URL` must be the URL users and AI clients use to reach CISO
Assistant, for example `https://grc.example.com`. Set the same value on the
backend and on `backend-mcp`.

The login redirects, the token issuer and the MCP resource are all built from
it. A wrong value makes sign-in fail.
{% endstep %}

{% step %}

#### Turn on self-registration

Clients like Copilot Studio and Claude Code register themselves. This is off by
default. Turn it on, on the backend **and** on `backend-mcp`:

```env
OAUTH_DCR_ENABLED=true
```

To accept only some clients, list the hosts they may send users back to after
sign-in:

```env
OAUTH_DCR_ALLOWED_REDIRECT_HOSTS=global.consent.azure-apim.net,localhost
```

`global.consent.azure-apim.net` is Copilot Studio. `localhost` covers Claude
Code and other clients that run on the user's machine. Leave the variable empty
to accept any host. Redirects must use HTTPS, except for loopback addresses.
{% endstep %}

{% step %}

#### Allow the write tools

`backend-mcp` is read-only by default: the write tools are hidden whatever the
profile. To make them available to the profiles that allow creating or
updating:

```env
CA_MCP_READ_ONLY=false
```
{% endstep %}

{% step %}

#### Turn MCP on and choose who may connect

Both are **off by default**: an instance does not accept any AI app until an
administrator decides so.

1. Go to **Extra** > **Settings** > **Feature flags** and turn on **AI app
   connections (MCP)**.
2. Allow the users who may connect an app: in **Organization** > **Users**,
   edit a user and tick **Can connect AI apps (MCP)**, or select several users
   and use **Allow AI apps**. Users who can connect show an **AI apps** badge.

Unticking a user, or deactivating them, disconnects all their apps at once.
Turning the feature flag off blocks every connection but keeps them: they work
again when you turn it back on.
{% endstep %}

{% step %}

#### Check the setup

Each of these must return `200`:

```bash
H=grc.example.com
for p in /.well-known/oauth-protected-resource/mcp \
         /.well-known/oauth-authorization-server/api \
         /api/.well-known/openid-configuration; do
  curl -s -o /dev/null -w "%{http_code} $p\n" "https://$H$p"
done
```

`/mcp` without a token must return `401` (`403` means the feature flag is off).
{% endstep %}
{% endstepper %}

{% hint style="warning" %}
**Apps that register themselves are not checked by anyone.** The consent page
says so, and shows where the app will send the user back. They can only reach
`/mcp`. Their tokens are refused on the REST API (`/api`).
{% endhint %}

### Connect a client

#### Microsoft Copilot Studio

1. On your agent, go to **Tools** > **Add a tool** > **New tool** > **Model
   Context Protocol**.
2. Enter the server name, a precise description, and the URL ending in `/mcp`.
3. For authentication, choose **OAuth 2.0**, type **Dynamic discovery**.
4. Create the connection. A browser window opens on CISO Assistant. Sign in,
   then click **Authorize**.

The app shows up as **Credential Manager** on the consent page and in
**Connected apps**. That's the name Copilot Studio registers with.

Copilot Studio runs in Microsoft's cloud, so it must reach your instance over
HTTPS from the internet. See [Making it reachable](mcp.md#making-it-reachable).

#### Claude Code

```bash
claude mcp add --transport http ciso-assistant https://<your-instance>/mcp
```

Then run `/mcp` in Claude Code, pick **ciso-assistant** and choose
**Authenticate**. A browser opens on the CISO Assistant login page.

#### Other clients

Any MCP client that supports OAuth works the same way: give it the URL ending
in `/mcp` and no token. To test the setup without an AI client, use the
[MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```bash
npx @modelcontextprotocol/inspector
```

Set the transport to **Streamable HTTP**, enter the URL, and use **Open Auth
Settings** > **Quick OAuth Flow**.

### Manage connected apps (users)

Go to your profile icon > **Settings** > **Security settings** > **Connected apps**. The table lists
every app that can access your account:

| Column     | Meaning                                                              |
| ---------- | -------------------------------------------------------------------- |
| App        | The name the app gave                                                |
| Returns to | Where the app sends you back after sign-in. This identifies the app  |
| Allowed actions | What the app may do, from the profile you picked when you approved it |
| Last used  | The last call the app made. Updated at most once a minute            |

<figure><img src="../.gitbook/assets/mcp-oauth-connected-apps.png" alt=""><figcaption><p>Connected apps in the security settings: Claude Code and apps that are authorized but not used yet</p></figcaption></figure>

If your administrator has not allowed your account to connect apps, this
section says so instead of showing the table.

To cut an app's access, click the trash icon on its row, then **Submit**. It
stops working right away. To connect again, it must ask for your approval
again.

<figure><img src="../.gitbook/assets/mcp-oauth-revoke-confirm.png" alt=""><figcaption><p>Revoking MCP Inspector asks for confirmation first</p></figcaption></figure>

{% hint style="info" %}
An app whose profile doesn't allow what you need will not fix itself. Revoke
it, or clear its sign-in in the client (in Claude Code: `/mcp` > **Clear
authentication**), then connect again and pick another profile.
{% endhint %}

### Manage connections (administrators)

Go to **Organization** > **Connected apps**. The page lists the connections of
every user: user, app, where it sends users back, allowed actions, the date it was
authorized and when it was last used. Search by user or app.

- The **trash icon** revokes one user's connection to one app.
- The **revoke for everyone** icon cuts an app for all its users, for example
  after an incident. Copilot Studio registers again for each connection, so
  CISO Assistant groups the registrations that share the same name and the same
  return address, and tells you how many users and registrations are affected
  before you confirm. An app that registered itself is also deleted; it can
  register again later, and users have to approve it again.

### Audit and limits

**Changes made through an app say so.** When an AI app creates or changes data,
the audit log entry keeps the user as the actor and also records the app: its
name, its client ID and the profile used (`via_app` in the entry). Audit events
forwarded to a SIEM carry it too: as `actor.app_name` and `actor.app_uid` in
OCSF, and as `via_app` in the raw format.

**Every tool call is logged**, reads included, in the `backend-mcp` logs. Each
`mcp tool call` line has the user, the app, the profile and its actions, the tool, the
outcome (`ok`, `refused`, `limited` or `error`), the duration and the size of
the answer. Collect these logs like the other service logs to see what an app
read, not only what it changed.

**Each connection has a budget**, on top of the size limit of a single answer:

- at most 60 tool calls per minute (`MCP_MAX_CALLS_PER_MINUTE`);
- at most 2,000,000 characters returned per hour, about a hundred full pages
  (`MCP_MAX_RESPONSE_CHARS_PER_HOUR`).

A connection is one user with one app. When it goes over, the tool answers with
an error that tells the agent to wait, and the call is logged as `limited`. Set
a variable to `0` to turn that limit off.

The counters are kept in the cache. With the default in-memory cache, each
worker counts on its own and the counters reset on restart; use a shared cache
for exact limits.

### Personal Access Tokens still work

`backend-mcp` also accepts a PAT, sent as `Authorization: Bearer <PAT>`. Existing
setups that use **API key** authentication keep working. Profiles don't apply
to a PAT: it gets the user's full permissions.

### Troubleshooting

#### "You cannot connect this app" during sign-in

The user's account is not allowed to connect AI apps, or the feature is off for
the whole instance. The page says which. See
[Turn MCP on and choose who may connect](#turn-mcp-on-and-choose-who-may-connect).

<figure><img src="../.gitbook/assets/mcp-oauth-refused.png" alt=""><figcaption><p>The refusal page when AI app connections are off for the instance. <strong>Back to the app</strong> tells the app the user refused</p></figcaption></figure>

#### `/mcp` answers `403` "MCP is disabled by your administrator."

The **AI app connections (MCP)** feature flag is off.

#### The client says the server has no registration endpoint

`OAUTH_DCR_ENABLED` is not `true` on both the backend and `backend-mcp`. Set it
on both and recreate the two services.

#### Sign-in loops back to the login page, or fails with a redirect error

`CISO_ASSISTANT_URL` does not match the URL in the browser. Use the same URL for
the instance, the client and the setting.

#### Registration fails with "Redirect host is not allowed"

The client's callback host is not in `OAUTH_DCR_ALLOWED_REDIRECT_HOSTS`. Add it,
or leave the variable empty.

#### A tool says the connection made too many calls, or read its data budget

The connection went over one of the limits in [Audit and limits](#audit-and-limits).
The agent can wait and continue. If normal use hits it, raise
`MCP_MAX_CALLS_PER_MINUTE` or `MCP_MAX_RESPONSE_CHARS_PER_HOUR` on `backend-mcp`.

#### A tool says the connection's profile does not allow it

The user picked a profile that doesn't allow that action. They can reconnect
the app and pick another profile. If the
write tools are missing entirely, check that `CA_MCP_READ_ONLY=false`.

#### `/api` answers "This client can only access the MCP endpoint."

This is expected. Tokens of apps that registered themselves only work on `/mcp`.
For REST API access, use a [PAT](pat.md) or a [service account](service-accounts.md).

#### `421 Misdirected Request`

The `Host` header is not in `CA_MCP_ALLOWED_HOSTS`. See
[Making it reachable](mcp.md#making-it-reachable).

#### `502 Bad Gateway` on the login page, behind a tunnel or a second proxy

Some proxies reject large response headers. The CISO Assistant frontend sends a
large `Link` header (page preload hints). Raise the proxy's header buffer size,
or remove the `Link` header at your proxy. It's only a speed hint.

### Environment variables

| Variable                           | Service              | Default                      | Description                                                                     |
| ---------------------------------- | -------------------- | ---------------------------- | ------------------------------------------------------------------------------- |
| `CISO_ASSISTANT_URL`               | backend, backend-mcp | -                            | Public URL of the instance. Must be the same on both services                   |
| `OAUTH_DCR_ENABLED`                | backend, backend-mcp | `false`                      | Let MCP clients register themselves                                             |
| `OAUTH_DCR_ALLOWED_REDIRECT_HOSTS` | backend              | -                            | Comma-separated hosts a self-registered client may redirect to. Empty means any |
| `OAUTH_REFRESH_TOKEN_IDLE_DAYS`    | backend              | `30`                         | Days without use after which an app must be approved again. `0` means never     |
| `CA_MCP_READ_ONLY`                 | backend-mcp          | `true`                       | Hide the write tools                                                            |
| `CA_MCP_ALLOWED_HOSTS`             | backend-mcp          | host of `CISO_ASSISTANT_URL` | Accepted `Host` headers, port included                                          |
| `MCP_MAX_CALLS_PER_MINUTE`         | backend-mcp          | `60`                         | Tool calls allowed per connection per minute. `0` means no limit                |
| `MCP_MAX_RESPONSE_CHARS_PER_HOUR`  | backend-mcp          | `2000000`                    | Characters returned per connection per hour. `0` means no limit                 |
