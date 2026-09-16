# Send all outbound mail through one service built on Django `MAILERS`, with SMTP as the default

- Status: Proposed
- Deciders: @nas-tabchiche, @ab-smith

## Context

Today we send mail over plain SMTP. There is a primary server and an optional rescue server. Both are configured with `EMAIL_HOST` and related environment variables.

Three parts of the code send mail on their own: `iam/models.py`, `core/tasks.py` and `automation/workflows/tasks.py`. Only the first one falls back to the rescue server. The code checks "is mail configured?" in three different ways. All three assume an SMTP host exists.

Two things outside the project force a change.

First, Microsoft 365 and Google Workspace are dropping password login for SMTP. Google did it in May 2025. Microsoft turns it off by default for existing tenants in January 2027, and new tenants cannot use it at all. Customers who host with them need one of: OAuth over SMTP, the Microsoft Graph API, or an HTTP mail provider.

Second, Django 6.1 added `MAILERS`. It is a setting for named mail backends, shaped like `DATABASES`. At the same time Django deprecated everything we use today: the `EMAIL_*` settings, `get_connection()`, the `connection` argument and `fail_silently`.

Our own production sends through SendGrid's SMTP relay. Neither change affects it. It must keep working with its current configuration.

## Decision

We will build one mail service in `core`. Every outbound message goes through it.

The service reads two named mailers from `MAILERS`: `default` and `rescue`. If `default` fails, it retries with `rescue`. This applies to every message.

Operators keep using environment variables. The existing SMTP and rescue variables keep working unchanged. A new variable, `EMAIL_TRANSPORT`, selects the mailer type. It defaults to `smtp`. The allowed values are a fixed list in the code.

Besides SMTP, the list covers the HTTP providers that django-anymail fully supports, plus a Microsoft Graph backend that we write ourselves.

Templates, i18n and the task queue do not change. Huey stays.

## Consequences

### Rules

- All application code sends mail through the service. Using `EmailMessage`, `get_connection()` or `EMAIL_*` settings anywhere else is forbidden.
- Environment variable names are a public interface. SMTP and rescue variables keep their names and meaning. Each new transport adds its own variables with its own prefix. Operators never pass a backend class path. An unknown `EMAIL_TRANSPORT` value stops startup.
- Startup logging in `settings.py` prints hosts, ports and usernames only. It never prints passwords, API keys or client secrets.
- Every new transport must be one more entry in the allowed list. The service itself must not change to add one.
- We document only the Anymail providers that Anymail marks as Full. SendGrid is documented as SMTP only.
- We update the README, the RHEL packaging and the product-docs mailer page for each transport. This includes how to set up SPF, DKIM and DMARC for the domain in `DEFAULT_FROM_EMAIL`. The customer owns DNS. We can document it, not enforce it.

### Version 1

- The mail service in `core`, with the `default` and `rescue` aliases read from `MAILERS`. The two aliases are independent. Each can be any allowed type. Fallback applies to every send, not only password resets. Every fallback writes an error log that includes the primary failure.
- `EMAIL_TRANSPORT=smtp` (the default) maps the existing variables to `MAILERS` unchanged. In `MAIL_DEBUG` mode, the console backend becomes the `default` mailer.
- One function, `mailing_enabled()`, replaces all "is mail configured?" checks. It reads `MAILERS`. The `EMAIL_HOST or EMAIL_HOST_RESCUE` checks and the required-settings list in `core/tasks.py` are removed. A Django system check stops startup if a mailer is set but `DEFAULT_FROM_EMAIL` is not.
- django-anymail as a required dependency, exposing the providers Anymail marks as Full today: Amazon SES, Brevo, MailerSend, Mailgun, Mailjet, Mailtrap, Postmark, Resend, Scaleway TEM, SparkPost and Unisender Go. Anymail has not been able to test its SendGrid backend since June 2025, so production stays on the SMTP relay.
- A Microsoft Graph backend that we write and maintain ourselves. It is roughly sixty lines: get a token from Entra with `msal` client credentials, then call the Graph `sendMail` endpoint as the configured mailbox. The alternative is a third-party package. The two that exist, django-msgraphbackend and django-o365, each have a single maintainer. We would rather own sixty lines than depend on one person for code that handles credentials. The cost is ours: we follow Graph API changes and fix bugs ourselves.
- The service sends synchronously. It tries `default`, then `rescue`. If both fail, it raises. It never hides an error. Callers that must not block wrap the call in a Huey task. That task is responsible for the result: it must report success or failure to whoever asked for the mail. The workflow `send_email` action already works this way since #4654, and is the model to follow. A task that catches the error, logs it and moves on is not acceptable when a user asked for the mail. Password reset and invitations stay inline in version 1. They can move into a task later without changing the service.
- A "send test email" action for administrators. It sends only to the administrator's own address. It reports which alias was used, the backend type, and the error if there was one.

### Later

- OAuth over SMTP (XOAUTH2) for Microsoft 365 and Google Workspace. One SMTP backend subclass that fetches the token and authenticates with it. Until then, Microsoft 365 customers use Graph and Google Workspace customers use the IP-allowlisted relay.

### Out of scope

- Delivery webhooks, bounce tracking and inbound mail. We add no new inbound endpoint.
- Templates, i18n and the task queue. Huey stays.

## Security considerations

- New kinds of secrets appear in the environment: provider API keys and an Entra client secret. We treat them like the SMTP password today: environment only, never logged, never exposed through the API.
- The Graph `Mail.Send` application permission covers the whole tenant by default. Our code only sends as the configured mailbox. But if the secret leaks, nothing on our side stops an attacker from sending as any mailbox. The customer documentation requires an `ApplicationAccessPolicy` that limits the app to the sending mailbox. We accept that we cannot check whether the customer did this.
- HTTP providers receive message content, including recipient addresses and notification text, outside the customer's network. The operator chooses this by picking the transport. The default stays SMTP.
- The fixed list of transports in code prevents loading arbitrary classes from an environment variable.
- The test-send action is limited to administrators and to their own address, so it cannot be used as a relay. It is rate limited.
- If the primary mailer is misconfigured, the rescue mailer may carry all traffic without anyone noticing. This is a monitoring gap, not a breach. The error log on every fallback is the mitigation.
- We accept that django-anymail and its `requests` dependency join the supply chain, and that we maintain a small Graph client ourselves.

## Alternatives considered

- **SMTP only, and tell Microsoft 365 customers to use High Volume Email or a local relay**: rejected. HVE only delivers to internal recipients. A relay just moves the problem to the customer.
- **django-msgraphbackend or django-o365 for Graph**: rejected. Both are single-maintainer packages, and the code we need is about sixty lines.
- **Anymail's SendGrid backend for production**: rejected. It is untested upstream. The SMTP relay is a supported Twilio product.
- **django-post_office**: rejected. It duplicates the Huey queue and adds a database outbox we do not need.
- **django.tasks instead of Huey**: rejected. Django ships no worker, and Huey is already in place.
- **Keep fallback per caller (status quo)**: rejected. Notifications and workflow mail have no fallback today.
- **Queue every message and let the task swallow errors (the pre-#4654 notification path)**: rejected. A queue is fine, dropping the failure is not. The task that sends must report the outcome to whoever triggered the mail.
- **Let operators provide a `MAILERS` dict or a backend class path**: rejected. It allows loading arbitrary code and creates combinations we would have to debug.
- **OAuth over SMTP in the first delivery**: deferred. Graph covers Microsoft 365 and the IP-allowlisted relay covers Google Workspace.
- **One mailer, no rescue alias**: rejected. Existing deployments rely on the rescue server.
