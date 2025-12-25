---
description: Configure Microsoft Entra ID as an Identity Provider for CISO Assistant
---

# Microsoft Entra ID

Go into your **Azure portal home**

1.  Open the sidebar menu and click on **Microsoft Entra ID**<br>

    <figure><img src="../../../.gitbook/assets/entra-sso-step-1.png" alt=""><figcaption></figcaption></figure>
2.  Click on **Add button > Entreprise application**<br>

    <figure><img src="../../../.gitbook/assets/entra-sso-step-2.png" alt=""><figcaption></figcaption></figure>
3.  Click on **Create your own application**<br>

    <figure><img src="../../../.gitbook/assets/entra-sso-step-3.png" alt=""><figcaption></figcaption></figure>
4.  Enter a name and then click **Integrate any other application you don’t find in the gallery (Non-gallery)**<br>

    <figure><img src="../../../.gitbook/assets/entra-sso-step-4.png" alt=""><figcaption></figcaption></figure>
5.  Click on **Single sign-on** from the sidebar menu or on **Set up single sign on** bellow Getting Started and choose **SAML**<br>

    <figure><img src="../../../.gitbook/assets/entra-sso-step-5-1.png" alt=""><figcaption></figcaption></figure>



    <figure><img src="../../../.gitbook/assets/entra-sso-step-5-2.png" alt=""><figcaption></figcaption></figure>
6. In the first box **Basic SAML Configuration**, specify the **Entity ID**, it has to be the same than <mark style="color:purple;">**SP Entity ID**</mark> in CISO Assistant (see next screenshot)
7.  Add the **Reply URL**: `<base_url>/api/accounts/saml/0/acs/`  (for example with localhost: `https://localhost:8443/api/accounts/saml/0/acs/`)<br>

    <figure><img src="../../../.gitbook/assets/entra-sso-step-6-7.png" alt=""><figcaption></figcaption></figure>
8. In the third box **SAML Certificates**, copy the **App Federation Metadata Url** as it is the <mark style="color:purple;">**Metadata URL**</mark>  in CISO Assistant (see next screenshot)
9.  In the fourth box **Set up \<App\_name>**, copy the **Microsoft Entra Identifier** as it is the <mark style="color:purple;">**IdP Entity ID**</mark> in CISO Assistant<br>

    <figure><img src="../../../.gitbook/assets/entra-sso-step-8-9.png" alt=""><figcaption></figcaption></figure>
10. Make sure you use the same Identifier (Entity ID) that you've set earlier and appear on block 1, on CISO Assistant SP Entity ID:\
    <img src="../../../.gitbook/assets/image (10).png" alt="" data-size="original">&#x20;
11. Click on **Users and groups** in the sidebar menu, and **Add user/group** to give them access to CISO Assistant with SSO. The matching key will be the email and you'll be able to grant their permissions on the applications.<br>

    <figure><img src="../../../.gitbook/assets/entra-sso-step-10.png" alt=""><figcaption></figcaption></figure>

{% hint style="warning" %}
<mark style="color:orange;">Add a user in your application doesn't automatically create the user on CISO Assistant</mark>
{% endhint %}

You can now [configure CISO Assistant](../#configure-ciso-assistant-with-saml) with the <mark style="color:purple;">**3 parameters**</mark> you've retrieved.



### Using Open ID connect



* head to Entra ID
* Under manage, select `App registrations` and create a `New registration` and use the default settings.
* Once createad, copy the `Application (client) ID` and use it as first parameter on CISO Assistant.
* under the manage section of the app, select `certificates and secrets`
* Create a `new client secret` under the client secrets, copy its value and use it as second parameter on CISO Assistant.
* Go back to Overview of the app, and click Endpoints. Use the value on `OpenID Connect metadata document` as third parameter on CISO Assistant.
* Under the `Authentication (Preview)` of the app, click `add redirect URI`, and select `web` , the value should be something like `<ciso_assistant_backend_url>/api/accounts/oidc/openid_connect/login/callback/` for instance, for localhost, `http://localhost:8000/api/accounts/oidc/openid_connect/login/callback/`



