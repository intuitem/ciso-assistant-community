# Compose service accounts from existing User/Client/SocialApp objects, not a first-class machine-identity model

- Status: Accepted
- Deciders: @tchoumi313, @eric-intuitem, @nas-tabchiche

## Context

CISO Assistant needed machine-to-machine access to its own API, for two cases: a script or CI job that can hold a secret we mint (local), and an org that already runs its machine identities through its own IdP (Entra ID workload identities, Auth0 M2M, Okta, a self-hosted Keycloak, etc.) and wants that IdP's token to authorize calls directly, with no secret minted or stored on our side (federated).

The tempting design is a first-class "machine identity" or "application" concept in the IAM model, parallel to `User`, with its own authentication and its own permission-checking path. We rejected that shape for both cases. In both, an object already in the codebase is the thing we needed: allauth's own OIDC provider `Client` model already implements `client_credentials` for the local case, and `allauth.socialaccount.models.SocialApp` already is a registered app for a specific external provider instance, which is the exact shape needed to register a specific external client for the federated case, and it already backs every other external-IdP integration in the codebase (human SSO).

## Decision

We will keep `ServiceAccount` as a thin coordination record over existing objects, never a first-class authentication or authorization principal of its own:

- a credential source, either an allauth `Client` (local: holds `client_id` plus a hashed secret, `client_credentials` grant only) or a `SocialApp` reference (federated: an externally-issued token verified against that provider's own signing keys, no `Client` at all);
- a dedicated internal `User`, the actual principal our permission system operates on. It has an unusable password and a non-routable service-accounts email, and it should be straightforward to exclude from human-facing surfaces (users list, editor seat counting, role-assignment views for humans) with a simple flag or FK check, not a parallel data model;
- a `Role` plus a domain-scoped assignment, in the same shape as a human's: either a dedicated role holding exactly the permissions granted, or linked to a shared built-in role so its permissions track that role live.

Authentication for both cases should be new code that plugs into the permission-checking system we already have for humans, not a parallel one. Whatever resolves a bearer credential to a service account, whether a local secret or a federated token, should hand back the account's `User` and let the existing role/permission/domain-scoping logic take it from there. Nothing downstream of authentication should need to know or branch on whether it is looking at a human or a machine.

## Consequences

- No new permission-checking path. Whatever already decides what a `User` can see and do keeps deciding it; it does not need a machine-specific variant.
- No custom token issuance or validation logic for the local case. This is allauth's own `client_credentials` grant; we do not build our own crypto, signing, or expiry handling for it.
- No parallel "trusted machine IdP" registry for the federated case. It is the same `SocialApp` rows human SSO already uses, so registering one for a service account shares that existing surface instead of duplicating it.
- Both identity sources should share one authorization surface. A service account can be custom-permissions, role-linked, or global-admin regardless of whether its credential is local or federated; there should be no reduced-capability "federated mode" for authorization, only for secret management.
- Deactivation, deletion, and seat-counting should reuse whatever lifecycle already exists for `User` and `Role`, not grow a separate one for machine principals.
- Decisions specific to the federated case, following from reusing `SocialApp` rather than a bespoke model:
  - No JIT: an admin has to register the specific external client before any token from it is accepted. A validly signed token from the right issuer but an unregistered client should still be refused. The client identifier on the `SocialApp` row is itself the registration, so no second "registered clients" table is needed.
  - IdP role or permission claims are never read for authorization. Our own role assignment stays the sole source of truth; no external IdP has a concept of our folder hierarchy.
  - No secret is ever stored locally for a federated account, and rotating a secret is not something a federated account can do; key rotation is the identity provider's responsibility.
  - The signature verification has to pin the algorithm to whatever the provider's own published key says it is, never trust an algorithm claimed by the token itself, to close off algorithm-confusion attacks by construction rather than by a denylist.
  - Discovery and key documents should be cached rather than fetched on every request, and a provider that is down or unreachable should simply refuse the request rather than error out.
  - The identity source and which external client and subject a federated account maps to should not be editable after creation. Changing any of that means deleting and recreating the account.
  - Registering or updating an identity provider should actively check that it is reachable and correctly configured at that moment, so a typo surfaces immediately instead of on the first real caller.
  - SCIM stays human-only. Federated service accounts are a distinct concept from SCIM user and group provisioning, not folded into that surface.

## Alternatives considered

- A first-class "machine identity" or "application" principal, distinct from `User`, with its own permission resolution: rejected, it would force every permission-checking code path to become polymorphic over two kinds of principal, for no behavioral gain over "it's a `User`."
- A bespoke local token-issuance endpoint, floated in an earlier design pass: rejected in favor of allauth's own OIDC `Client` and `client_credentials` grant, already implemented and already tested, with less attack surface than hand-rolled token issuance.
- A bespoke pair of models to represent a trusted external IdP and its registered clients, for the federated case: rejected, `SocialApp` already covers the same shape and is shared with human SSO instead of adding a parallel registration surface.
- Scoping federation to SAML as well as OIDC: rejected. SAML has a bearer assertion convention for exchanging an assertion for a token, but nothing equivalent to presenting a bearer credential directly on every API call, so "any IdP" for machine-to-machine auth means any OIDC-compliant one in practice.
- Letting IdP role or authorization claims (for example Entra's roles) broaden access: rejected, our RBAC stays entirely local; an IdP claim should never be able to grant more than the account's own role assignment allows.
- Restricting federated accounts to custom permissions only, with no role-linking or global-admin: this was the first cut shipped. Rejected once dual-mode authorization already existed for local accounts; forking authorization behavior by identity source was more surprising than useful, so federated accounts were given the same options instead.
