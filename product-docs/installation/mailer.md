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

For local development you can run [Mailpit](https://github.com/axllent/mailpit) and point `EMAIL_HOST` at it with both flags set to `False`.

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

### OAuth 2.0 over SMTP (Microsoft 365, Google Workspace, others)

Microsoft 365 and Google Workspace no longer accept a mailbox password for SMTP. CISO Assistant can authenticate with an OAuth 2.0 token instead. The session is still SMTP: same host, same port, same firewall rules. Set `EMAIL_TRANSPORT=smtp-oauth2`, then give the token endpoint, the grant and the credentials. The same variables exist with a `_RESCUE` suffix for the second mailer.

`EMAIL_HOST_USER` is the mailbox mail is sent as. `EMAIL_HOST_PASSWORD` is not used.

There are no provider presets in the application. The blocks below are the values for the two common providers; any provider that follows the OAuth 2.0 standards works the same way.

#### Microsoft 365

```bash
EMAIL_TRANSPORT=smtp-oauth2
EMAIL_HOST=smtp.office365.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@example.com
DEFAULT_FROM_EMAIL=noreply@example.com
EMAIL_OAUTH2_GRANT_TYPE=client_credentials
EMAIL_OAUTH2_TOKEN_URL=https://login.microsoftonline.com/<tenant id>/oauth2/v2.0/token
EMAIL_OAUTH2_SCOPE=https://outlook.office365.com/.default
EMAIL_OAUTH2_CLIENT_ID=<application (client) id>
EMAIL_OAUTH2_CLIENT_SECRET=<client secret>
```

On the tenant side:

1. Register an application in Entra ID and create a client secret.
2. Do not grant `SMTP.SendAsApp` tenant-wide in Entra. Grant it through Exchange RBAC for Applications with a management scope limited to the sending mailbox, so a leaked secret cannot send as anyone else. Grants from Entra and Exchange add up, so an Entra grant would undo the scope.
3. Enable SMTP AUTH on that one mailbox (`Set-CASMailbox -SmtpClientAuthenticationDisabled $false`). OAuth does not bypass the SMTP AUTH switch.

#### Google Workspace

```bash
EMAIL_TRANSPORT=smtp-oauth2
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@example.com
DEFAULT_FROM_EMAIL=noreply@example.com
EMAIL_OAUTH2_GRANT_TYPE=jwt_bearer
EMAIL_OAUTH2_TOKEN_URL=https://oauth2.googleapis.com/token
EMAIL_OAUTH2_SCOPE=https://mail.google.com/
EMAIL_OAUTH2_SERVICE_ACCOUNT_FILE=/run/secrets/mailer-service-account.json
```

On the Workspace side, create a service account, download its JSON key, and grant it domain-wide delegation for the scope `https://mail.google.com/`.

{% hint style="warning" %}
SMTP with OAuth on Google requires the full mail scope, and domain-wide delegation cannot be limited to one mailbox. A leaked key can read and send as any user in the domain. If that is not acceptable, use the IP-allowlisted SMTP relay (`smtp-relay.gmail.com`) with `EMAIL_TRANSPORT=smtp` and no credentials instead.
{% endhint %}

#### Any other provider

Use the same variables with the values from the provider's documentation. `refresh_token` additionally needs `EMAIL_OAUTH2_REFRESH_TOKEN`. `jwt_bearer` needs either `EMAIL_OAUTH2_SERVICE_ACCOUNT_FILE` or `EMAIL_OAUTH2_ISSUER` plus `EMAIL_OAUTH2_PRIVATE_KEY`, and optionally `EMAIL_OAUTH2_AUDIENCE` when it differs from the token URL. The token URL must use https. It may point at a private identity provider.

Tokens are cached until shortly before they expire. A token the server rejects is refreshed and retried once; a second rejection counts as an unreachable mailer and the next configured mailer, if any, is tried.
