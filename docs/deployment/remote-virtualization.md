---
description: Experimenting CISO Assistant through remote server or hypervisor
---

# Remote/Virtualization



{% hint style="warning" %}
New: Use the config builder at the `config` folder of the repo for an interactive and reliable experience.
{% endhint %}

Let's say that you want to setup or experiment with CISO Assistant on a Network or Virtualized environment (eg. Hypervisor) on a remote host, for instance, to use with multiple users:



<figure><img src="../.gitbook/assets/image (10).png" alt=""><figcaption></figcaption></figure>

* Install a recent version of Docker on your remote server
* Given that we are using TLS with Caddy, we need to have DNS entries and not IPs
* The workstations need to be able to reach the remote using an FQDN (DNS entry). If not you can add an entry on your `/etc/hosts`. Keep track of the remote server DNS as you'll put it on the next step, let's say the remote is `cool-vm` for instance
* Clone the repo, but don't run anything yet. **Edit** the `docker-compose.yml` file as follows:\
  (red is for deletion and green for addition); your diff should look like:

<figure><img src="../.gitbook/assets/image (13).png" alt=""><figcaption></figcaption></figure>

* Five lines need to be edited. Save the file and move to the next step

If you're getting `SSL_ERROR_INTERNAL ERROR_ALERT` (Can be different on other browsers) blocking you from continuing, make sure that you've made the 5 changes above.

<mark style="color:purple;">The</mark> <mark style="color:purple;"></mark><mark style="color:purple;">`tls internal`</mark> <mark style="color:purple;"></mark><mark style="color:purple;">(equivalent to</mark> <mark style="color:purple;"></mark><mark style="color:purple;">`-i`</mark> <mark style="color:purple;"></mark><mark style="color:purple;">in CLI mode) parameter of Caddy can present some security issues and is not recommended for production and internet exposure. You should consider proper certificates for that.</mark>



You're all set, and you can simply run:

```
./docker-compose.sh
```

Your CISO Assistant can be reached now from  `https://cool-vm:8443`, and you can skip the SSL warning for the self-signed certificate.
