# OpenID Connect (OIDC)

### Configure CISO Assistant with OpenID Connect (OIDC)

Once you've retrieved the **Client ID**, the **Client Secret** and the **Issuer URL** (sometimes called the discovery or `.well-known` URL) from your provider, the configuration on CISO Assistant is pretty simple.<br>

1.  Log in into CISO Assistant as an **administrator > Extra > Settings**

    <figure><img src="../../.gitbook/assets/image (9).png" alt=""><figcaption></figcaption></figure>
2.  Navigate to **SSO** settings

    <figure><img src="../../.gitbook/assets/image (2) (1) (1) (1).png" alt=""><figcaption></figcaption></figure>
3.  **Enable SSO**

    <figure><img src="../../.gitbook/assets/image (3) (1) (1) (1).png" alt=""><figcaption></figcaption></figure>
4.  Select the **OpenID Connect** provider

    <figure><img src="../../.gitbook/assets/image (4) (1) (1) (1).png" alt=""><figcaption></figcaption></figure>
5.  Enter the **Client ID**

    <figure><img src="../../.gitbook/assets/image (5) (1).png" alt=""><figcaption></figcaption></figure>
6.  Enter the **Client secret**

    <figure><img src="../../.gitbook/assets/image (6) (1).png" alt=""><figcaption></figcaption></figure>
7. Enter the **Server URL**
8. And that's it! Don't forget to **click the 'Save' button**
9. You should now be able to see the **Login with SSO** button

<div align="left" data-full-width="false"><figure><img src="../../.gitbook/assets/image (8).png" alt="" width="375"><figcaption></figcaption></figure></div>

{% hint style="warning" %}
<mark style="color:orange;">Be aware that the user needs to be created on CISO Assistant to be authenticated with SSO.</mark>
{% endhint %}

{% hint style="info" %}
CISO Assistant automatically sends a standards-compliant `state` and `nonce` on every OIDC authorization request (43 characters matching `^[A-Za-z0-9-._~]{43,128}$`), and validates the `nonce` claim returned in the `id_token`. No configuration is required. This is helpful for identity providers that enforce format or length constraints on these parameters. Per OIDC Core 3.1.3.7, the `nonce` sent in the authorization request must be present and match in the `id_token` — a missing or mismatched nonce will reject the login.
{% endhint %}

### Single Logout

Turn on **Enable service provider-initiated single logout** in the SSO settings to close the OIDC session at the identity provider when users log out of CISO Assistant (see [Single Logout](README.md#single-logout) for the general behavior). It additionally requires:

* an `end_session_endpoint` in the provider's OpenID configuration, and
* `<frontend_url>/login` registered as an allowed post-logout redirect URI on the OIDC client.

CISO Assistant calls the end-session endpoint with `client_id`, `id_token_hint`, and that post-logout redirect URI.

{% hint style="info" %}
With Microsoft Entra ID, OIDC logout still prompts the user to select an account, because Entra ignores the standard `id_token_hint`. The logout itself works, but the prompt cannot be suppressed without Entra-specific configuration. For a prompt-free single logout with Entra ID, use SAML instead.
{% endhint %}
