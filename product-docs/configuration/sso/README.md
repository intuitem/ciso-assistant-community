---
description: Configure Single Sign-On with different SAML or OpenID Connect providers
---

# SSO

### Documented providers

* [Microsoft Entra ID](identity-providers/entra-id.md)
* [Okta](identity-providers/okta.md)
* [Keycloak](identity-providers/keycloak.md)
* [Google Workspace](identity-providers/google-workspace.md)

### Forcing SSO and local-login exceptions

Enabling SSO adds the **Log in with SSO** button but leaves the email/password form in place, so users can still authenticate locally. To make SSO the only way in, turn on **Force SSO Login** in the SSO settings.

When Force SSO Login is enabled, local password authentication is disabled for everyone — a user who tries the password form is rejected with _"This user is not allowed to use local login."_

To keep a few accounts able to log in locally (typically break-glass administrators, or a service account used while the identity provider is being set up), enable the per-user **Keep local login** flag on their user record. These accounts continue to work through the standard password form even while SSO is forced.

Some accounts are exempt automatically and always keep local login:

* **Superusers**, so an administrator can never be locked out.
* **Third-party users** (portal / TPRM accounts).

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
