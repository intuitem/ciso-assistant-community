# Compose service accounts from existing User/Client/SocialApp objects, not a first-class machine-identity model

- Status: Accepted
- Deciders: @tchoumi313, @eric-intuitem, @nas-tabchiche

## Context

CISO Assistant needed machine-to-machine API access for two cases: a script or CI job holding a secret we mint (local), and an org that already runs its machine identities through its own IdP (Entra, Auth0, Okta, a self-hosted Keycloak) and wants that IdP's token to authorize calls directly, with no secret stored on our side (federated). The tempting design is a first-class "machine identity" concept parallel to `User`. We rejected that: allauth's own `Client` model already implements `client_credentials` for the local case, and `SocialApp` already is a registered external-provider app, the exact shape needed for federation, and it already backs human SSO.

## Decision

`ServiceAccount` stays a thin coordination record over existing objects, never a first-class principal of its own: a credential source (`Client` for local, a `SocialApp` reference for federated), a dedicated internal `User` (the actual principal our permission system operates on, excluded from human-facing surfaces by a simple flag or FK check, not a parallel model), and a `Role` plus domain-scoped assignment shaped exactly like a human's. Authentication for both cases is new code that plugs into the permission-checking system we already have; nothing downstream of authentication should branch on human versus machine.

## Consequences

- No new permission-checking path, no custom token issuance for the local case (it is allauth's own grant), no parallel IdP registry for the federated case (the same `SocialApp` rows human SSO already uses).
- Sharing that table is not sharing live configuration: SSO keeps its own copy and never reads `SocialApp` at request time, so editing one side cannot silently affect the other, but the two can drift apart.
- Both identity sources share one authorization surface: custom, role-linked, or global-admin, regardless of whether the credential is local or federated.
- Deactivation, deletion, and seat-counting reuse whatever lifecycle already exists for `User` and `Role`, not a separate one for machines.
- Federated-specific, following from reusing `SocialApp`: no JIT, the client id on the row is itself the registration; IdP role or permission claims are never read for authorization; no secret is ever stored locally and rotation is not possible; the verification algorithm is pinned to whatever the provider's own key says, never trusted from the token; discovery and keys are cached, an unreachable provider just refuses the request; the identity source is immutable after creation, while the provider and subject a federated account maps to can be changed, each change rechecked live; registering a provider does a live reachability check; SCIM stays human-only.

## Security considerations

**Conclusion: service accounts add a machine credential that can call the API, but no new authorization path. A stolen credential gives exactly the role it was assigned, in the domains it was assigned, until it is revoked or expires.**

### Threat model

What is worth protecting: the API rights of each service account, and the human SSO configuration that shares the `SocialApp` table. Attackers we assume: an unauthenticated caller presenting forged or replayed tokens, a holder of a leaked local secret, a compromised or misconfigured external IdP, and an admin pointing a provider at an internal URL. New trust boundary: for federated accounts, we trust a token signed by a key the external IdP publishes.

### Why the attack fails

1. **One principal, one permission path.** Each account acts through a dedicated `User` with a role and domain-scoped assignment, checked by the same code as humans. Nothing downstream of authentication branches on human versus machine.
2. **Only global admins manage accounts**, behind the `service_accounts` feature flag (`ServiceAccountViewSet` in `iam/views.py`).
3. **Local secrets are never stored in clear.** allauth hashes the client secret; it is shown once, on create or rotate. Access tokens last one hour (`IDP_OIDC_ACCESS_TOKEN_EXPIRES_IN`).
4. **Federated tokens are verified strictly** (`iam/oidc_federation.py`): signature, issuer, audience equal to the registered client id, and `exp` all required; the algorithm comes from the provider's key, never from the token, so `none` and HS256 key confusion fail; the token's `sub` must match the registered subject.
5. **IdP claims never grant rights.** Roles and permissions stay local.
6. **No probing.** An unknown client and subject pair fails with the same error as a bad token on a registered one.
7. **No SSRF through the provider.** Discovery and key URLs go through `assert_public_url_unless_dev` on every fetch, not only at registration, and redirects are refused.
8. **Fail closed.** Once the cached discovery document and keys expire, an unreachable provider refuses the request. A key lookup miss triggers at most one refetch per provider every five seconds. Federated accounts have their expiry checked on every request, not only by the daily deactivation task.

### Verification

`iam/tests/test_service_accounts.py` (local accounts, roles, expiry) and `iam/tests/test_federated_service_accounts.py` (wrong subject, issuer, audience or key, `alg: none`, HS256 confusion, missing `exp` or `sub`, future `nbf`, expired account before the cron runs, unknown pair indistinguishable from a bad token, rate-limited key refresh, live check failing closed). Seat counting: `enterprise/backend/tests/test_seat_enforcement.py`.

### Remaining risks, accepted as low

- **A compromised IdP can mint valid tokens** for the subjects mapped to it, with those accounts' rights. That is the meaning of federation. Deactivating the account cuts access at once.
- **A key the IdP revokes stays trusted for up to 30 minutes**, the key cache lifetime (`JWKS_CACHE_TTL`), including while the provider is unreachable. Deactivating the account is the immediate response.
- **An expired local account keeps working until the daily deactivation task runs**, at most about a day. Local authentication checks only `is_active`; the task deactivates the account and deletes its tokens.
- **Federated tokens cannot be revoked on our side**, and their lifetime is the IdP's choice. Revocation is deactivation of the account.
- **A leaked local secret works until rotated.** Rotation allows a grace period of up to 30 days, during which both secrets work.
- **With `ALLOW_PRIVATE_NETWORK_REQUESTS` set, the URL guard is off**, so a provider may point at internal hosts. Operators set it knowingly, for an IdP on a private network.

### What would change this assessment

- Reading any IdP claim for authorization, or adding JIT creation of federated accounts.
- Letting non-global-admins create or edit service accounts.
- A code path that treats a service account user differently from a human after authentication.
- Raising the key cache lifetime or allowing redirects on discovery or key fetches.

## Alternatives considered

- A first-class "machine identity" principal, distinct from `User`: rejected, would force every permission-checking path to become polymorphic for no behavioral gain.
- A bespoke local token-issuance endpoint: rejected in favor of allauth's own `client_credentials` grant, already implemented and tested.
- A bespoke pair of models for a trusted external IdP and its clients: rejected, `SocialApp` already covers that shape and is shared with human SSO.
- Scoping federation to SAML as well as OIDC: rejected, nothing in SAML is equivalent to presenting a bearer credential on every API call.
- Letting IdP role claims broaden access: rejected, our RBAC stays entirely local.
- Restricting federated accounts to custom permissions only: this shipped first, then rejected once dual-mode authorization already existed for local accounts.
