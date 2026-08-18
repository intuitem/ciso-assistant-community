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
- Federated-specific, following from reusing `SocialApp`: no JIT, the client id on the row is itself the registration; IdP role or permission claims are never read for authorization; no secret is ever stored locally and rotation is not possible; the verification algorithm is pinned to whatever the provider's own key says, never trusted from the token; discovery and keys are cached, an unreachable provider just refuses the request; the identity source, client, and subject a federated account maps to are immutable after creation; registering a provider does a live reachability check; SCIM stays human-only.

## Alternatives considered

- A first-class "machine identity" principal, distinct from `User`: rejected, would force every permission-checking path to become polymorphic for no behavioral gain.
- A bespoke local token-issuance endpoint: rejected in favor of allauth's own `client_credentials` grant, already implemented and tested.
- A bespoke pair of models for a trusted external IdP and its clients: rejected, `SocialApp` already covers that shape and is shared with human SSO.
- Scoping federation to SAML as well as OIDC: rejected, nothing in SAML is equivalent to presenting a bearer credential on every API call.
- Letting IdP role claims broaden access: rejected, our RBAC stays entirely local.
- Restricting federated accounts to custom permissions only: this shipped first, then rejected once dual-mode authorization already existed for local accounts.
