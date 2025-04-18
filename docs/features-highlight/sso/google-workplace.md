---
description: Configure Google Workplace as an Identity Provider for CISO Assistant
---

# Google Workplace

{% hint style="danger" %}
<mark style="color:red;">Google Workspace doesn't allow callbacks to urls containing</mark> <mark style="color:red;"></mark><mark style="color:red;">`http`</mark> <mark style="color:red;"></mark><mark style="color:red;">or</mark> <mark style="color:red;"></mark><mark style="color:red;">`localhost`</mark> <mark style="color:red;"></mark><mark style="color:red;">so it can be tricky to test it locally. You should deploy CISO Assistant with a FQDN to bypass these restrictions.</mark>
{% endhint %}

Go into **Google Workspace Admin console**

1.  On the sidebar menu, go to **Applications** > **Web and mobile applications**

    <figure><img src="../../.gitbook/assets/image (19).png" alt=""><figcaption></figcaption></figure>
2.  Click on **Add an application** > **Add a custom SAML Application**

    <figure><img src="../../.gitbook/assets/image (20).png" alt=""><figcaption></figcaption></figure>
3.  Enter **ciso-assistant** or the name of your choice and click on **continue**

    <figure><img src="../../.gitbook/assets/image (23).png" alt=""><figcaption></figcaption></figure>
4.  You can copy the <mark style="color:purple;">**SSO URL**</mark>, <mark style="color:purple;">**Entity Id**</mark> and <mark style="color:purple;">**x509 certificate**</mark> here but you'll be able to retreive them later

    <figure><img src="../../.gitbook/assets/image (24).png" alt=""><figcaption></figcaption></figure>
5.  Fill **ACS URL** with `<base_url>/api/accounts/saml/0/acs/`, enter the **Entity ID** which has to be the same than <mark style="color:purple;">**SP entity Id**</mark> in CISO Assistant (**ciso-assistant** by default) and choose **Email** in **Name ID Format**\


    <figure><img src="../../.gitbook/assets/image (25).png" alt=""><figcaption></figcaption></figure>
6.  Add two mappings for **First name** and **Last Name**, fill them with those two values: `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname`\
    `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname`

    <figure><img src="../../.gitbook/assets/image (26).png" alt=""><figcaption></figcaption></figure>
7.  On application home page, you can now find the <mark style="color:purple;">**Entity ID**</mark>, <mark style="color:purple;">**SSO URL**</mark> and <mark style="color:purple;">**x509 certificate**</mark>\


    <figure><img src="../../.gitbook/assets/image (27).png" alt=""><figcaption></figcaption></figure>

{% hint style="warning" %}
<mark style="color:orange;">Add a user in your application doesn't automatically create the user on CISO Assistant</mark>
{% endhint %}

You can now [configure CISO Assistant](https://intuitem.gitbook.io/ciso-assistant/features-highlights/sso#configure-ciso-assistant-with-saml) with the <mark style="color:purple;">**3 parameters**</mark> you've retrieved.
