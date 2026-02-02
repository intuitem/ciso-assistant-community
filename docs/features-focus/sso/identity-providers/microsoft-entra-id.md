---
description: Configure Microsoft Entra ID as an Identity Provider for CISO Assistant
---

# Microsoft Entra ID

{% tabs %}
{% tab title="SAML" %}


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


12. You can now [configure CISO Assistant](../#configure-ciso-assistant-with-saml) with the <mark style="color:purple;">**3 parameters**</mark> you've retrieved.
{% endtab %}

{% tab title="OIDC" %}
#### 1. Introduction

Go to your Microsoft Azure Portal

![Introduction](https://static.guidde.com/v0/qg%2FIEuhINveF1g6sYuIJ0IpcFfUJDz2%2Frk5UfQgUTG1bXn6gWdkGLo%2Fm4G5LxhDhqZY4sSpYhSGjd_doc.png?alt=media\&token=04407fa3-8e47-422c-9e4c-bcd259e24484)

#### 2. Navigate to App Registrations

Click the App registrations section to add a new application for OIDC configuration. You can also use the search bar if you don't find it in the suggestions.

![Navigate to App Registrations](https://static.guidde.com/v0/qg%2FIEuhINveF1g6sYuIJ0IpcFfUJDz2%2Frk5UfQgUTG1bXn6gWdkGLo%2F6dcTNYFYT7zChVjPkeqre1_doc.png?alt=media\&token=428002ca-9fdb-442d-ba79-fc1e7669548b)

#### 3. Start New Application Registration

![Start New Application Registration](https://static.guidde.com/v0/qg%2FIEuhINveF1g6sYuIJ0IpcFfUJDz2%2Frk5UfQgUTG1bXn6gWdkGLo%2Fn1ck8yYsiBMzghUPSN3Dar_doc.png?alt=media\&token=033fd114-1ec0-46cc-94dc-fb716357048f)

#### 4. Name your application

![Name your application](https://static.guidde.com/v0/qg%2FIEuhINveF1g6sYuIJ0IpcFfUJDz2%2Frk5UfQgUTG1bXn6gWdkGLo%2FuWGj4A8xJKEtJT2i2wVDot_doc.png?alt=media\&token=3475459a-00cf-4dea-be4d-1b411d008d57)

#### 5. Select Web Platform in Redirect URI options

![Select Web Platform in Redirect URI options](https://static.guidde.com/v0/qg%2FIEuhINveF1g6sYuIJ0IpcFfUJDz2%2Frk5UfQgUTG1bXn6gWdkGLo%2FpgpbWJE36ZGMCBp1ZNpr9Q_doc.png?alt=media\&token=744b2a8d-dfa7-4670-b469-f78d1ef19aa6)

#### 6. Enter the callback URL of your instance

The callback URL is: `<ciso_assistant_url>/api/accounts/oidc/openid_connect/login/callback/` for

for instance, for localhost: `http://localhost:8000/api/accounts/oidc/openid_connect/login/callback/`

![Enter the callback URL of your instance](https://static.guidde.com/v0/qg%2FIEuhINveF1g6sYuIJ0IpcFfUJDz2%2Frk5UfQgUTG1bXn6gWdkGLo%2F9LgYQFoBu4jzwReWtZ8RQj_doc.png?alt=media\&token=cb4a3f36-94a7-4adc-b1f6-bd45d1a052cb)

#### 7. Complete Application Registration

![Complete Application Registration](https://static.guidde.com/v0/qg%2FIEuhINveF1g6sYuIJ0IpcFfUJDz2%2Frk5UfQgUTG1bXn6gWdkGLo%2FaE46UDqv6Qj353WczPYjib_doc.png?alt=media\&token=f9eda0d1-d7c1-4c35-adec-6e6cc6162d40)

#### 8. Copy the Application Client ID

![Copy the Application Client ID](https://static.guidde.com/v0/qg%2FIEuhINveF1g6sYuIJ0IpcFfUJDz2%2Frk5UfQgUTG1bXn6gWdkGLo%2Fj4HxbA933shMF4YLiTQpKN_doc.png?alt=media\&token=7d23b6bd-824f-4e8e-ab24-c8d19cb76ef7)

#### 9. Past it into the Client ID field

![Past it into the Client ID field](https://static.guidde.com/v0/qg%2FIEuhINveF1g6sYuIJ0IpcFfUJDz2%2Frk5UfQgUTG1bXn6gWdkGLo%2FmfJwdmC6XW98TwQtBi1tDE_doc.png?alt=media\&token=f785e518-1d5b-4a5a-b329-56a767012b6e)

#### 10. Open Certificates & Secrets

![Open Certificates & Secrets](https://static.guidde.com/v0/qg%2FIEuhINveF1g6sYuIJ0IpcFfUJDz2%2Frk5UfQgUTG1bXn6gWdkGLo%2FtSEeuLJhWcgbv2kCSDFa5W_doc.png?alt=media\&token=c4cb2f78-ab54-4647-a3eb-7c7abe4231b9)

#### 11. Create a New Client Secret

![Create a New Client Secret](https://static.guidde.com/v0/qg%2FIEuhINveF1g6sYuIJ0IpcFfUJDz2%2Frk5UfQgUTG1bXn6gWdkGLo%2F2bUjbaZCmeRE4tAm5wXYmV_doc.png?alt=media\&token=b04156e4-b8d4-45ee-846d-81364ffce675)

#### 12. Add your Client Secret

![Add your Client Secret](https://static.guidde.com/v0/qg%2FIEuhINveF1g6sYuIJ0IpcFfUJDz2%2Frk5UfQgUTG1bXn6gWdkGLo%2FquPjbc42FSLh4gdRxQtNbJ_doc.png?alt=media\&token=91060f91-e8ca-47fa-9204-7bdc5445ac29)

#### 13. Copy the fresh Client Secret Value

![Copy the fresh Client Secret Value](https://static.guidde.com/v0/qg%2FIEuhINveF1g6sYuIJ0IpcFfUJDz2%2Frk5UfQgUTG1bXn6gWdkGLo%2FfhUvXygLkKLWcU2FRbUWCm_doc.png?alt=media\&token=19ce3280-9d37-4066-940d-a8056e6c292f)

#### 14. Past it into the Secret field

![Past it into the Secret field](https://static.guidde.com/v0/qg%2FIEuhINveF1g6sYuIJ0IpcFfUJDz2%2Frk5UfQgUTG1bXn6gWdkGLo%2FdeXjQnv7rSz5g9VfNd6iqJ_doc.png?alt=media\&token=72bbf1c7-548e-4acc-abf9-07981f7cdeb5)

#### 15. Go back to your App Overview

![Go back to your App Overview](https://static.guidde.com/v0/qg%2FIEuhINveF1g6sYuIJ0IpcFfUJDz2%2Frk5UfQgUTG1bXn6gWdkGLo%2Fs9M4ELtFdgpD3XUBov8yzi_doc.png?alt=media\&token=59fb365d-fd30-4a1e-9169-fc2288ef6300)

#### 16. Inside Endpoints copy the OpenID Connect metadata URL

![Inside Endpoints copy the OpenID Connect metadata URL](https://static.guidde.com/v0/qg%2FIEuhINveF1g6sYuIJ0IpcFfUJDz2%2Frk5UfQgUTG1bXn6gWdkGLo%2Fek7LxvurULGuoRMHnd5CaE_doc.png?alt=media\&token=e60904ee-e5bb-4229-9aca-dff74b73a177)

#### 17. Paste it into the Server URL field

![Paste it into the Server URL field](https://static.guidde.com/v0/qg%2FIEuhINveF1g6sYuIJ0IpcFfUJDz2%2Frk5UfQgUTG1bXn6gWdkGLo%2Fk4VkipPBEeDSWX95eva89a_doc.png?alt=media\&token=959cd638-397a-465f-8502-1d8a0a8369d9)

#### 18. Save your configuration

![Save your configuration](https://static.guidde.com/v0/qg%2FIEuhINveF1g6sYuIJ0IpcFfUJDz2%2Frk5UfQgUTG1bXn6gWdkGLo%2FdecHPQUuEQRJt82tDzpzkA_doc.png?alt=media\&token=38769a0b-9b81-4013-9a86-6319b84b6de7)

{% hint style="success" %}
You have successfully configured OpenID Connect (OIDC) integration with EntraID.
{% endhint %}
{% endtab %}
{% endtabs %}

{% hint style="warning" %}
<mark style="color:orange;">Adding a user in your Entra application doesn't automatically create the user on CISO Assistant</mark>
{% endhint %}
