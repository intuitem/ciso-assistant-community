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
- a hidden **Role** holding exactly the permissions selected at creation;
- a **RoleAssignment** scoping that role to explicitly chosen perimeter
  folders (optionally recursive).

Existing RBAC applies untouched: an access token resolves to the service
account's user, and `RoleAssignment.is_access_allowed` does the rest.

## Management API (Global administrators only)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/iam/service-accounts/` | GET / POST | List / create (response includes the one-time `client_secret`) |
| `/api/iam/service-accounts/permissions/` | GET | Selectable permissions catalog (`[{value, label}]`) |
| `/api/iam/service-accounts/<id>/` | GET / PATCH / DELETE | Detail / update (incl. `is_active` toggle) / full teardown |
| `/api/iam/service-accounts/<id>/rotate-secret/` | POST | New secret (returned once); revokes outstanding tokens |

The client secret is hashed at rest and only ever returned by create and
rotate-secret. Deactivating a service account strips its grant types (blocking
new token issuance), revokes outstanding tokens, and deactivates its user.

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
account's permissions and perimeter folders:

```bash
curl -s http://localhost:8000/api/folders/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Tokens are opaque, expire after 3600 s (`IDP_OIDC_ACCESS_TOKEN_EXPIRES_IN`),
and are revoked by deactivation, secret rotation, and deletion.

## Signing key

The OIDC provider needs an RSA private key (`IDP_OIDC_PRIVATE_KEY`). It is
resolved in order from: the `IDP_OIDC_PRIVATE_KEY` environment variable, the
PEM file at `IDP_OIDC_PRIVATE_KEY_FILE` (default
`<BASE_DIR>/db/idp_oidc_private_key.pem`), or auto-generated on first start
(RSA 2048, file mode 0600).
