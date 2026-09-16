# Send all outbound mail through one service built on Django `MAILERS`, with SMTP as the default

- Status: Proposed
- Deciders: @nas-tabchiche, @ab-smith

## Context

Today we send mail over plain SMTP. There is a primary server and an optional rescue server. Both are configured with `EMAIL_HOST` and related environment variables.

Three parts of the code send mail on their own: `iam/models.py`, `core/tasks.py` and `automation/workflows/tasks.py`. Only the first one falls back to the rescue server. The code checks "is mail configured?" in three different ways. All three assume an SMTP host exists.

Two things outside the project force a change.

First, Microsoft 365 and Google Workspace are dropping password login for SMTP. Google did it in May 2025. Microsoft leaves it unchanged through December 2026, then disables it by default for existing tenants and makes it unavailable by default for tenants created after that date. Administrators can still re-enable it for now. Microsoft has not announced the final removal date. Customers who host with them need one of: OAuth over SMTP, the Microsoft Graph API, or an HTTP mail provider.

Second, Django 6.1 added `MAILERS`. It is a setting for named mail backends, shaped like `DATABASES`. At the same time Django deprecated everything we use today: the `EMAIL_*` settings, `get_connection()`, the `connection` argument and `fail_silently`.

Our own production sends through SendGrid's SMTP relay. Neither change affects it. It must keep working with its current configuration.

## Decision

We will build one mail service in `core`. Every outbound message goes through it.

The service reads the mailers from `MAILERS` and tries them in order until one accepts the message. There is no dedicated rescue mailer: a second mailer is just the next entry in the list.

Operators keep using environment variables. The existing SMTP variables keep working unchanged. A new variable, `EMAIL_TRANSPORT`, selects the type of the first mailer. It defaults to `smtp`. The allowed values are a fixed list in the code. The existing `_RESCUE` SMTP variables keep working and define a second, SMTP-only mailer.

Besides SMTP, the list covers the HTTP providers that django-anymail fully supports, plus a Microsoft Graph backend that we write ourselves.

Templates, i18n and the task queue do not change. Huey stays.

## Consequences

### Rules

- All application code sends mail through the service. Using `EmailMessage`, `get_connection()` or `EMAIL_*` settings anywhere else is forbidden.
- Environment variable names are a public interface. The SMTP variables and the `_RESCUE` variables keep their names and meaning. Documentation calls the latter the second mailer and stops using the word rescue. Each new transport adds its own variables with its own prefix. Operators never pass a backend class path. An unknown `EMAIL_TRANSPORT` value stops startup.
- Startup logging in `settings.py` prints hosts, ports and usernames only. It never prints passwords, API keys or client secrets.
- Every new transport must be one more entry in the allowed list. The service itself must not change to add one.
- We document only the Anymail providers that Anymail marks as Full. SendGrid is documented as SMTP only.
- We update the README, the RHEL packaging and the product-docs mailer page for each transport. This includes how to set up SPF, DKIM and DMARC for the domain in `DEFAULT_FROM_EMAIL`. The customer owns DNS. We can document it, not enforce it.

### Version 1

- The mail service in `core`. Settings build `MAILERS` from the environment: `EMAIL_TRANSPORT` defines the first mailer, and the `_RESCUE` variables, if set, define a second SMTP mailer. The service tries them in declaration order. Failover applies to every send, not only password resets. Every failover writes an error log naming the mailer that failed and the exception. That log is the server log, for operators. Surfaces a user sees, such as a workflow run log or an API error, get a generic message, as #4654 already does. Credentials never appear in either.
- The service fails over only when the failure happened before the message was handed over: connection refused, TLS or authentication failure, provider API unreachable. Two kinds of failure do not fail over. A permanent rejection of the message or recipient, because the next mailer would give the same answer. And a failure after the message was sent but before the server answered, such as a timeout waiting for the final response, because the server may have accepted it and a second mailer would send it twice. In that last case the service raises and says the outcome is unknown.
- `EMAIL_TRANSPORT=smtp` (the default) maps the existing variables to `MAILERS` unchanged. In `MAIL_DEBUG` mode, the console backend is the only mailer.
- One function, `mailing_enabled()`, replaces all "is mail configured?" checks. It reads `MAILERS`. The `EMAIL_HOST or EMAIL_HOST_RESCUE` checks and the required-settings list in `core/tasks.py` are removed. Settings refuse to load if a mailer is set but `DEFAULT_FROM_EMAIL` is not, the same way they already refuse `EMAIL_USE_TLS` together with `EMAIL_USE_SSL`. This runs wherever Django starts, including the RHEL service, which launches gunicorn without any `manage.py` step. A Django system check alone would not cover that path.
- django-anymail as a required dependency, exposing the providers Anymail marks as Full today: Amazon SES, Brevo, MailerSend, Mailgun, Mailjet, Mailtrap, Postmark, Resend, Scaleway TEM, SparkPost and Unisender Go. Anymail has not been able to test its SendGrid backend since June 2025, so production stays on the SMTP relay.
- A Microsoft Graph backend that we write and maintain ourselves. It is roughly sixty lines: get a token from Entra with `msal` client credentials, then call the Graph `sendMail` endpoint as the configured mailbox. The alternative is a third-party package. The two that exist, django-msgraphbackend and django-o365, each have a single maintainer. We would rather own sixty lines than depend on one person for code that handles credentials. The cost is ours: we follow Graph API changes and fix bugs ourselves.
- The service sends synchronously. It tries each mailer in order. If all fail, it raises. It never hides an error. Callers that must not block wrap the call in a Huey task. That task is responsible for the result: it must report success or failure to whoever asked for the mail. The workflow `send_email` action already works this way since #4654, and is the model to follow. A task that catches the error, logs it and moves on is not acceptable when a user asked for the mail. Password reset and invitations stay inline in version 1. They can move into a task later without changing the service.
- A "send test email" action for administrators. It sends only to the administrator's own address. It reports which mailer was used, its type, and the error if there was one.

### Later

- A generic way to declare any number of mailers of any type from the environment. Not needed until a customer wants a fallback that is not SMTP.
- OAuth over SMTP (XOAUTH2) for Microsoft 365 and Google Workspace. One SMTP backend subclass that fetches the token and authenticates with it. Until then, Microsoft 365 customers use Graph and Google Workspace customers use the IP-allowlisted relay.

### Out of scope

- Delivery webhooks, bounce tracking and inbound mail. We add no new inbound endpoint.
- Templates, i18n and the task queue. Huey stays.

## Security considerations

- New kinds of secrets appear in the environment: provider API keys and an Entra client secret. We treat them like the SMTP password today: environment only, never logged, never exposed through the API.
- A tenant-wide `Mail.Send` grant in Entra lets the app send as any mailbox. Our code only sends as the configured mailbox. But if the secret leaks, nothing on our side stops an attacker from sending as any other. The customer documentation therefore requires Exchange RBAC for Applications: assign the `Application Mail.Send` role to the app with a management scope limited to the sending mailbox, and grant no `Mail.Send` permission in Entra at all. Grants from the two systems add up, so an Entra grant would undo the scope. `ApplicationAccessPolicy` is the older mechanism that RBAC for Applications replaces; we do not document it. We accept that we cannot check whether the customer did any of this.
- HTTP providers receive message content, including recipient addresses and notification text, outside the customer's network. The operator chooses this by picking the transport. The default stays SMTP.
- The fixed list of transports in code prevents loading arbitrary classes from an environment variable.
- The test-send action is limited to administrators and to their own address, so it cannot be used as a relay. It is rate limited.
- If the first mailer is misconfigured, a later one may carry all traffic without anyone noticing. This is a monitoring gap, not a breach. The error log on every failover is the mitigation.
- We accept that django-anymail and its `requests` dependency join the supply chain, and that we maintain a small Graph client ourselves.

## Alternatives considered

- **SMTP only, and tell Microsoft 365 customers to use High Volume Email or a local relay**: rejected. HVE only delivers to internal recipients. A relay just moves the problem to the customer.
- **django-msgraphbackend or django-o365 for Graph**: rejected. Both are single-maintainer packages, and the code we need is about sixty lines.
- **Anymail's SendGrid backend for production**: rejected. It is untested upstream. The SMTP relay is a supported Twilio product.
- **django-post_office**: rejected. It duplicates the Huey queue and adds a database outbox we do not need.
- **django.tasks instead of Huey**: rejected. Django ships no worker, and Huey is already in place.
- **Keep failover per caller (status quo)**: rejected. Notifications and workflow mail have no failover today.
- **Keep a dedicated rescue mailer**: rejected. It is a special case of an ordered list, with its own name, settings block and code path, and it allows exactly one fallback.
- **Fail over on every error**: rejected. Retrying a permanent rejection on another mailer gives the same answer and can send the message twice.
- **Queue every message and let the task swallow errors (the pre-#4654 notification path)**: rejected. A queue is fine, dropping the failure is not. The task that sends must report the outcome to whoever triggered the mail.
- **Let operators provide a `MAILERS` dict or a backend class path**: rejected. It allows loading arbitrary code and creates combinations we would have to debug.
- **OAuth over SMTP in the first delivery**: deferred. Graph covers Microsoft 365 and the IP-allowlisted relay covers Google Workspace.
- **One mailer, no failover**: rejected. Existing deployments rely on the second SMTP server, and running two providers is a common setup.
