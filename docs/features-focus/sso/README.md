---
description: Configure Single Sign-On with different SAML or OpenID C providers
---

# SSO

[How to configure CISO Assistant](./#configure-ciso-assistant)

### Providers

* [Microsoft Entra ID](microsoft-entra-id.md)
* [Okta](okta.md)
* [Keycloak](keycloak.md)
* [Google Workspace](google-workplace.md)

### Configure CISO Assistant with SAML

Once you've retrieved the **IdP Entity ID,** the **Metadata URL** and the **Entity ID** from your provider (see the [list of providers](./#list-of-provider) for specific details), the configuration on CISO Assistant is pretty simple.

1.  Log in into CISO Assistant as an **administrator > Extra > Settings**\


    <figure><img src="../../.gitbook/assets/Screenshot 2024-09-02 12.31.25.png" alt=""><figcaption></figcaption></figure>
2.  **Enable SSO**

    <figure><img src="../../.gitbook/assets/Screenshot 2024-09-02 12.32.06.png" alt=""><figcaption></figcaption></figure>
3.  Enter the <mark style="color:purple;">**Idp Entity ID**</mark>\


    <figure><img src="../../.gitbook/assets/Screenshot 2024-09-02 12.32.42.png" alt=""><figcaption></figcaption></figure>
4.  Choose the option 1 or 2 depending of your provider and fill <mark style="color:purple;">**Metadata URL**</mark> or <mark style="color:purple;">**SSO URL**</mark>, <mark style="color:purple;">**SLO URL**</mark>, <mark style="color:purple;">**x509 certificate**</mark> retrieved from your provider\


    <figure><img src="../../.gitbook/assets/Screenshot 2024-09-02 12.33.52 (1).png" alt=""><figcaption></figcaption></figure>
5.  Check that the <mark style="color:purple;">**SP Entity ID**</mark> is similar to the **Entity/Client ID** specified on your provider\


    <figure><img src="../../.gitbook/assets/ciso-sso-step-4.png" alt=""><figcaption></figcaption></figure>
6. And that's it ! Don't forget to save changes
7.  You should now be able to see the **Login with SSO** button\


    <figure><img src="../../.gitbook/assets/ciso-sso-step-6.png" alt=""><figcaption></figcaption></figure>



### Configure CISO Assistant with OpenID Connect (OIDC)

Once you've retrieved the IdP Entity ID, the Metadata URL and the Entity ID from your provider (see the list of providers for specific details), the configuration on CISO Assistant is pretty simple.\


1.  Log in into CISO Assistant as an **administrator > Extra > Settings**

    <figure><img src="../../.gitbook/assets/image (9).png" alt=""><figcaption></figcaption></figure>
2.  Navigate to **SSO** settings

    <figure><img src="../../.gitbook/assets/image (2) (1).png" alt=""><figcaption></figcaption></figure>
3.  **Enable SSO**

    <figure><img src="../../.gitbook/assets/image (3) (1).png" alt=""><figcaption></figcaption></figure>
4.  Select the **OpenID Connect** provider

    <figure><img src="../../.gitbook/assets/image (4) (1).png" alt=""><figcaption></figcaption></figure>
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
