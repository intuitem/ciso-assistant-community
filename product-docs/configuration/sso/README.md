---
description: Configure Single Sign-On with different SAML or OpenID Connect providers
---

# SSO

### Documented providers

* [Microsoft Entra ID](identity-providers/entra-id.md)
* [Okta](identity-providers/okta.md)
* [Keycloak](identity-providers/keycloak.md)
* [Google Workspace](identity-providers/google-workspace.md)

### Single Logout

By default, logging out of CISO Assistant only ends the local CISO Assistant session. The identity provider session stays open, so clicking **Log in with SSO** again signs the user straight back in without re-authenticating.

To also close the identity provider session on logout, enable **Enable service provider-initiated single logout** in the SSO settings. When it is on, logging out of CISO Assistant redirects the browser through the identity provider's logout endpoint.

This is _service provider-initiated_ single logout: CISO Assistant asks the identity provider to end **its own** session for the user. Whether that in turn signs the user out of other applications federated to the same identity provider depends on the identity provider's single-logout configuration and is not something CISO Assistant controls or can guarantee.

The option is off by default, and each protocol needs a logout endpoint on the identity provider side:

* **OIDC** — the provider must expose an `end_session_endpoint`, and `<frontend_url>/login` must be registered as an allowed post-logout redirect URI. See [OpenID Connect](oidc.md).
* **SAML** — the identity provider Single Logout Service URL must be available (read from the metadata, or set in the **SLO URL** field). See [SAML](saml.md).

{% hint style="info" %}
Keep `CISO_ASSISTANT_URL` set to the public frontend URL, otherwise the post-logout redirect will not resolve.
{% endhint %}

### Forcing SSO and local-login exceptions

Enabling SSO adds the **Log in with SSO** button but leaves the email/password form in place, so users can still authenticate locally. To make SSO the only way in, turn on **Force SSO Login** in the SSO settings.

When Force SSO Login is enabled, local password authentication is disabled for everyone — a user who tries the password form is rejected with _"This user is not allowed to use local login."_

To keep a few accounts able to log in locally (typically break-glass administrators, or a service account used while the identity provider is being set up), enable the per-user **Keep local login** flag on their user record. These accounts continue to work through the standard password form even while SSO is forced.

Some accounts get **Keep local login** enabled by default when they are created:

* **Superusers** created with `createsuperuser` (or at first boot), so the initial administrator is not locked out.
* **Third-party users** (portal / TPRM accounts).

Note that this is only a default on the flag, not a permanent exemption: a regular user promoted to superuser afterwards does not get it automatically, and unticking **Keep local login** on any of these accounts removes their local access like anyone else.

SCIM-provisioned users, by contrast, are SSO-only by design.

{% hint style="warning" %}
Turning on Force SSO Login **clears the password** of every account that does not have **Keep local login** enabled. Set **Keep local login** on your exception accounts _before_ you enable Force SSO Login — otherwise their passwords are wiped, and re-enabling the flag afterwards does not restore them (the user has to go through a password reset, which requires a working mailer). Always confirm at least one break-glass account can still log in before forcing SSO.
{% endhint %}

### Direct SSO login link

By default the login page shows the standard email/password form alongside a **Log in with SSO** button. You can send users straight to your identity provider — skipping the form — by appending `?sso` to the login URL:

```
https://<your-instance>/login?sso
```

Opening that link starts the SSO redirect immediately, exactly as if the user had clicked **Log in with SSO**. It's convenient as a bookmark, or as the link you publish internally when SSO is the expected way in.

To send the user to a specific page after they authenticate, add a `next` parameter:

```
https://<your-instance>/login?sso&next=/analytics
```

{% hint style="info" %}
`?sso` only triggers the redirect when SSO is enabled. Users who are allowed to keep local login — for example break-glass administrators — can still reach the password form through the plain `/login` URL.
{% endhint %}
