---
description: Machine-to-machine API access for CISO Assistant, via OAuth2 client credentials
---

# Service accounts

A **service account** is an identity for a script, CI pipeline, or external system to call the CISO Assistant API on its own — no human, no session, no interactive login. It authenticates using the OAuth2 **client credentials** grant, fully delegated to the OIDC identity provider built into CISO Assistant.

{% hint style="info" %}
This is a **PRO** feature. It is gated by the `Service accounts` feature flag (see [feature-flags.md](../configuration/settings/feature-flags.md "mention")). While the flag is off, the **Service accounts** menu stays hidden and its API is unreachable.
{% endhint %}

### Creating a service account

Service accounts live under **Organization > Service accounts** in the sidebar, right next to Roles. Creating one asks for a **name**, an optional description, the **permissions** to grant — the same grouped picker used by [custom roles](../configuration/organization/custom-roles.md), by app and model — and the **domains** to scope it to.

<figure><img src="../.gitbook/assets/service-accounts-create-permissions.png" alt=""><figcaption><p>Name and grouped permission picker, shared with custom roles.</p></figcaption></figure>

Scrolling down, pick the **domains** (perimeter folders) the account can act on, with an option to extend the grant to their sub-domains automatically.

<figure><img src="../.gitbook/assets/service-accounts-create-domains.png" alt=""><figcaption><p>Domain scope and the "apply to sub-domains" option.</p></figcaption></figure>

{% hint style="warning" %}
On save, the **Client ID** and **Client secret** are shown once. <mark style="color:orange;">Copy the secret now — it cannot be retrieved again.</mark> If you lose it, use **Rotate secret** to issue a new one.
{% endhint %}

<figure><img src="../.gitbook/assets/service-accounts-secret.png" alt=""><figcaption><p>The client secret is shown only once, right after creation.</p></figcaption></figure>

### Using it: OAuth2 client credentials

```
curl https://<your-instance>/api/identity/o/api/token \
  -d "grant_type=client_credentials" \
  -u "<client_id>:<client_secret>"
```

This returns a bearer access token, scoped to the permissions and domains you granted. Use it like any other API token:

```
curl https://<your-instance>/api/users/ \
  -H "Authorization: Bearer <access_token>"
```

### Managing a service account

A service account's detail page shows its Client ID, scope, and granted permissions, alongside the actions to manage its lifecycle:

<figure><img src="../.gitbook/assets/service-accounts-detail.png" alt=""><figcaption><p>Edit, Deactivate, Rotate secret, Delete and Audit trail.</p></figcaption></figure>

* **Deactivate** immediately revokes any outstanding access token and blocks new ones from being issued — without deleting the account. **Activate** restores it.
* **Rotate secret** invalidates the current secret and issues a new one on the spot, keeping the same Client ID. Use it for routine credential rotation or if a secret leaks.
* **Delete** removes the underlying OAuth2 client entirely; its Client ID stops being valid.

Unlike a [PAT](pat.md), a service account isn't tied to a human user and doesn't expire on a fixed schedule — it lives until you deactivate or delete it, which makes it the right choice for long-running integrations rather than personal, short-lived API access.
