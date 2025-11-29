# SAML

{% tabs %}
{% tab title="General configuration" %}
### Configure CISO Assistant with SAML

Once you've retrieved the **IdP Entity ID,** the **Metadata URL** and the **Entity ID** from your provider (see the list of providers for specific details), the configuration on CISO Assistant is pretty simple.

1.  Log in into CISO Assistant as an **administrator > Extra > Settings**<br>

    <figure><img src="../../.gitbook/assets/Screenshot 2024-09-02 12.31.25.png" alt=""><figcaption></figcaption></figure>
2.  **Enable SSO**

    <figure><img src="../../.gitbook/assets/Screenshot 2024-09-02 12.32.06.png" alt=""><figcaption></figcaption></figure>
3.  Enter the <mark style="color:purple;">**Idp Entity ID**</mark><br>

    <figure><img src="../../.gitbook/assets/Screenshot 2024-09-02 12.32.42.png" alt=""><figcaption></figcaption></figure>
4.  Choose the option 1 or 2 depending of your provider and fill <mark style="color:purple;">**Metadata URL**</mark> or <mark style="color:purple;">**SSO URL**</mark>, <mark style="color:purple;">**SLO URL**</mark>, <mark style="color:purple;">**x509 certificate**</mark> retrieved from your provider<br>

    <figure><img src="../../.gitbook/assets/Screenshot 2024-09-02 12.33.52 (1).png" alt=""><figcaption></figcaption></figure>
5.  Check that the <mark style="color:purple;">**SP Entity ID**</mark> is similar to the **Entity/Client ID** specified on your provider<br>

    <figure><img src="../../.gitbook/assets/ciso-sso-step-4.png" alt=""><figcaption></figcaption></figure>
6. And that's it! Don't forget to save changes
7.  You should now be able to see the **Login with SSO** button<br>

    <figure><img src="../../.gitbook/assets/ciso-sso-step-6.png" alt=""><figcaption></figcaption></figure>
{% endtab %}

{% tab title="Advanced settings" %}
* **Allow single label domains**: This allows you to authenticate through SAML on a single-label domain (e.g. `https://ciso-assistant:8443`). If this is left unchecked, the only host forms allowed are:
  * IPv4
  * IPv6
  * FQDN (e.g. https://www.example.com/)
  * `localhost`
{% endtab %}
{% endtabs %}

{% hint style="warning" %}
<mark style="color:orange;">Be aware that the user needs to be created on CISO Assistant to be authenticated with SSO.</mark>
{% endhint %}
