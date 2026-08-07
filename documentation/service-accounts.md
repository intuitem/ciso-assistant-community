# Service accounts (OAuth2 client credentials)

Service accounts provide machine-to-machine access to the CISO Assistant API for
automations and integrations. They implement the standard OAuth2
`client_credentials` grant, fully delegated to django-allauth's OIDC identity
provider (`allauth.idp.oidc`) — no custom token logic.

## Model

A service account bundles four objects, managed as one unit:

- an **allauth OIDC Client** (confidential, `client_credentials` grant only) —
  holds the `client_id` and the hashed client secret;
- a dedicated internal **User** (unusable password, non-routable
  `sa-<client_id>@service-accounts.local` email) — hidden from the users list
  and excluded from editor seat counting;
- a **Role**, in one of two modes: **dedicated** (a hidden Role holding
  exactly the permissions selected) or **role-linked** (the account's `role`
  FK points directly at a shared built-in Role, e.g. `BI-RL-AUD`, so its
  permissions track that role live). `ServiceAccount.delete()` never deletes
  a linked role. Editing a role-linked account with different permissions
  detaches it: a new dedicated Role is forked with those permissions, the
  shared role is left untouched;
- a **RoleAssignment** scoping that role to explicitly chosen domain
  folders (optionally recursive).

Existing RBAC applies untouched: an access token resolves to the service
account's user, and `RoleAssignment.is_access_allowed` does the rest.
`RoleAssignmentViewSet` excludes service-account-owned assignments by
`user__service_account`, not by role — so a human sharing a role-linked
account's role stays visible in the admin's role-assignments list.

## Management API (Global administrators only)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/iam/service-accounts/` | GET / POST | List / create — `role` (builtin role id) XOR `permissions` (dedicated); response includes the one-time `client_secret` |
| `/api/iam/service-accounts/permissions/` | GET | Selectable permissions catalog (`[{id, codename, normalized_codename, content_type, ...}]`, same shape as the custom-roles permission picker) |
| `/api/iam/service-accounts/roles/` | GET | Built-in roles (`[{id, name, global_only, permissions}]`) — link directly, or seed the permission picker as a starting point |
| `/api/iam/service-accounts/<id>/` | GET / PATCH / DELETE | Detail / update (incl. `is_active` toggle) / full teardown |
| `/api/iam/service-accounts/<id>/rotate-secret/` | POST | New secret (returned once); accepts `grace_period_days` (0-30); revokes outstanding tokens |

The client secret is hashed at rest and only ever returned by create and
rotate-secret; both responses also include `secret_preview` (prefix + a few
characters, masked) for display in the UI without ever re-exposing the full
secret. Deactivating a service account strips its grant types (blocking
new token issuance), revokes outstanding tokens, and deactivates its user.

`is_recursive` defaults to `true`. The **Administrator** builtin role
(`BI-RL-ADM`, "all permissions") is meant for the explicit global-admin case
only: the UI's "Global administrator" mode links it with the Global folder,
recursive, and the regular role picker does not propose it (`global_only` in
the roles catalog). The API itself does not restrict the combination — an
admin can grant anything through custom permissions anyway. For domain-scoped
admin automation, use the Domain Manager role.

## Token flow

Request an access token from the allauth token endpoint:

```bash
curl -s -X POST http://localhost:8000/api/identity/o/api/token \
  -d "grant_type=client_credentials" \
  -d "client_id=<CLIENT_ID>" \
  -d "client_secret=<CLIENT_SECRET>"
# {"access_token": "...", "token_type": "Bearer", "expires_in": 3600}
```

Then call the API with the bearer token — access is limited to the service
account's permissions and domains:

```bash
curl -s http://localhost:8000/api/folders/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Tokens are opaque, expire after 3600 s (`IDP_OIDC_ACCESS_TOKEN_EXPIRES_IN`),
and are revoked by deactivation, secret rotation, and deletion. There is no
refresh token for `client_credentials` (none is issued for this grant per
RFC 6749 §4.4.3) — callers just request a new token with the same
`client_id`/`client_secret` once the current one expires.

Client secrets are generated as `ServiceAccount.SECRET_PREFIX` (`ca_sa.`) followed
by the random secret, e.g. `ca_sa.<random>`.

## Signing key

The OIDC provider needs an RSA private key (`IDP_OIDC_PRIVATE_KEY`). It is
resolved in order from: the `IDP_OIDC_PRIVATE_KEY` environment variable, the
PEM file at `IDP_OIDC_PRIVATE_KEY_FILE` (default
`<BASE_DIR>/db/idp_oidc_private_key.pem`), or auto-generated on first start
(RSA 2048, file mode 0600).
