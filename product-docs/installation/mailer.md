---
description: >-
  CISO Assistant uses SMTP to send transactional emails (password reset,
  superuser creation, notifications). This page covers configuration and the TLS
  specifics introduced in 3.16.
---

# Setting up mailer

### Environment variables

```bash
EMAIL_HOST=smtp.example.com
EMAIL_PORT=465
EMAIL_HOST_USER=noreply@example.com
EMAIL_HOST_PASSWORD=<secret>
DEFAULT_FROM_EMAIL=noreply@example.com

# Pick ONE of the two (not both):
EMAIL_USE_SSL=True    # SMTPS (typically port 465)
EMAIL_USE_TLS=False

# or
EMAIL_USE_SSL=False
EMAIL_USE_TLS=True    # STARTTLS (typically port 587)
```

For local development you can run [MailHog](https://github.com/mailhog/MailHog) and point `EMAIL_HOST` at it with both flags set to `False`.

### TLS certificate requirements (3.16+)

{% hint style="info" %}
Since 3.16, the backend image runs **rootless** and **read-only**, and ships with a recent Python/OpenSSL stack that enables strict X.509 verification (`VERIFY_X509_STRICT` + `VERIFY_X509_PARTIAL_CHAIN`).
{% endhint %}

This has two consequences:

1. The old recipe of running `update-ca-certificates` from `command:` in `docker-compose.yaml` **no longer works** — it requires root and write access to `/etc/ssl/certs/`, both denied by the new container. See the deprecated section below if you are still on an older image.
2. Every certificate in the chain presented by your SMTP server must satisfy the strict checks. A single non-compliant intermediate will fail the whole verification.

Your SMTP server certificate **and every certificate in its chain** must include:

* **BasicConstraints** — `CA:FALSE` on the leaf, `CA:TRUE` on intermediates and root
* **KeyUsage** — at minimum `digitalSignature, keyEncipherment` on the leaf
* **Authority Key Identifier (AKI)** — on every cert in the chain, not only the leaf
* a complete `fullchain` (leaf + intermediates), served in order by the SMTP server

If you get an error like:

```
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
Missing Authority Key Identifier (_ssl.c:1081)
```

regenerate the offending certificate with the missing extension. Inspect a cert with:

```bash
openssl x509 -in cert.pem -noout -text | grep -A1 "Authority Key Identifier\|Basic Constraints\|Key Usage"
```

### Trusting a private / self-signed CA

You cannot modify the system trust store at runtime anymore. Instead, mount a PEM file containing the CA(s) to trust and point OpenSSL at it via `SSL_CERT_FILE`:

```yaml
services:
  backend:
    image: ghcr.io/intuitem/ciso-assistant-community/backend:3.16.1
    environment:
      - EMAIL_HOST=smtp.example.com
      - EMAIL_PORT=465
      - EMAIL_USE_SSL=True
      - EMAIL_USE_TLS=False
      - SSL_CERT_FILE=/certs/ca-bundle.pem
    volumes:
      - ./ca-bundle.pem:/certs/ca-bundle.pem:ro
```

How it works:

* Django's mailer goes through `smtplib`, which builds its TLS context with `ssl.create_default_context()`.
* That function asks OpenSSL to load its default trust store.
* When `SSL_CERT_FILE` is set, OpenSSL uses **that file instead** of the system bundle (`/etc/ssl/certs/ca-certificates.crt`).

Requirements for the bundle file:

* A **single PEM file**, concatenating your root CA and any intermediates needed to validate the SMTP server's chain.
* Each cert in the bundle must itself satisfy the strict X.509 checks listed above (BasicConstraints, KeyUsage, AKI).

{% hint style="info" %}
`REQUESTS_CA_BUNDLE` is only honored by the `requests`/`urllib3` libraries (used by outbound HTTP calls such as OIDC/SAML metadata fetch). It has **no effect on SMTP**, so you don't need to set it for the mailer.
{% endhint %}

### Verifying the setup

From the backend container:

```bash
python -c "import smtplib, ssl; \
ctx = ssl.create_default_context(); \
s = smtplib.SMTP_SSL('smtp.example.com', 465, context=ctx); \
print(s.noop()); s.quit()"
```

A clean `(250, b'2.0.0 OK')` means TLS and trust are correctly configured. Any `SSL: CERTIFICATE_VERIFY_FAILED` will name the missing extension or the failing cert.

You can also trigger a password reset from the UI and watch the backend logs — failures are logged at `iam.models` with `email_host`, `email_port`, and the underlying SSL error.

### Deprecated: rescue mailer

{% hint style="warning" %}
The `EMAIL_*_RESCUE` variables (a secondary mailer used as fallback) are deprecated and will be removed in a future release. They are not a workaround for TLS issues — fix the certificate instead.
{% endhint %}

### Deprecated: `update-ca-certificates` recipe (pre-3.16)

{% hint style="danger" %}
This section is kept for users still on backend images older than 3.16. **Do not use it on 3.16+** — the recipe silently fails on the rootless/read-only container. Use the CA bundle method instead.
{% endhint %}

Older versions ran the container as root with a writable filesystem, which allowed mounting a CA at runtime and refreshing the trust store from `command:`:

```yaml
services:
  backend:
    image: ghcr.io/intuitem/ciso-assistant-community/backend:<old-tag>
    environment:
      - EMAIL_HOST=smtp.example.com
      - EMAIL_PORT=465
      - EMAIL_USE_SSL=True
      - SSL_CERT_FILE=/etc/ssl/certs/smtp.example.com.pem
    volumes:
      - ./smtp-fullchain.crt:/etc/ssl/certs/smtp.example.com.pem:ro
    command: |
      sh -c 'update-ca-certificates && <original entrypoint>'
```

When upgrading to 3.16+, remove the `command:` override and switch to the CA bundle method above.
