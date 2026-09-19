# Send all outbound mail through one service built on Django `MAILERS`, with SMTP as the default

- Status: Proposed
- Deciders: @nas-tabchiche, @ab-smith

## Context

Today we send mail over plain SMTP, with a primary server and an optional rescue server configured through `EMAIL_HOST` and related environment variables. Three parts of the code send mail on their own: `iam/models.py`, `core/tasks.py` and `automation/workflows/tasks.py`. Only the first falls back to the rescue server, and every "is mail configured?" check assumes an SMTP host exists.

Two things outside the project force a change. Microsoft 365 and Google Workspace are dropping password login for SMTP. Google already has. Microsoft disables it by default at the end of 2026 and has not dated the final removal. Customers hosted there need OAuth over SMTP or the Microsoft Graph API. Separately, Django 6.1 added `MAILERS`, a named-backend setting shaped like `DATABASES`, and deprecated everything we use today: the `EMAIL_*` settings, `get_connection()`, the `connection` argument and `fail_silently`.

Our own production sends through SendGrid's SMTP relay. Neither change affects it. It must keep working with its current configuration.

## Decision

We will build one mail service in `core`. Every outbound message goes through it. The service reads the mailers from `MAILERS` and tries them in order until one accepts the message. There is no dedicated rescue mailer: a second mailer is just the next entry in the list.

Operators keep using environment variables. The existing SMTP variables keep working unchanged. A new variable, `EMAIL_TRANSPORT`, selects the type of the first mailer and defaults to `smtp`. The allowed values are a fixed list in the code. The existing `_RESCUE` variables keep working and define a second, SMTP-only mailer. Besides plain SMTP, we add OAuth over SMTP for Microsoft 365 and Google Workspace, and a Microsoft Graph backend that we write ourselves. Templates, i18n and the task queue do not change.

## Consequences

### Rules

- All application code sends mail through the service. Using `EmailMessage`, `get_connection()` or `EMAIL_*` settings anywhere else is forbidden.
- Environment variable names are a public interface. The SMTP and `_RESCUE` variables keep their names and meaning. Each new transport adds its own prefixed variables. Operators never pass a backend class path. An unknown `EMAIL_TRANSPORT` value stops startup.
- Startup logging prints hosts, ports and usernames only. Secrets never appear in logs.
- Adding a transport means adding one entry to the allowed list. The service does not change.
- Each transport ships with its documentation in the README, the RHEL packaging and the product-docs mailer page, including SPF, DKIM and DMARC for the sending domain. The customer owns DNS.

### What we build

- The service, with `MAILERS` built from the environment and failover on every send. The SMTP mailer is our own subclass of Django's backend. It carries `EMAIL_FORCE_TLS_1_2` and the OAuth variant.
- OAuth over SMTP (XOAUTH2). The SMTP subclass obtains a token, with Entra client credentials for Microsoft 365 or a service account for Google Workspace, and presents it instead of a password. The session stays SMTP: same host, same port, same firewall rules on the customer side.
- A Microsoft Graph backend: `msal` client credentials, then Graph `sendMail` as the configured mailbox. For tenants that keep SMTP AUTH disabled. We write it rather than depend on a single-maintainer package for code that handles credentials, and we carry the maintenance.
- Failover happens only when a mailer could not be reached: for SMTP, when opening the connection fails; for Graph, when the request never reached Microsoft. Once a message has been handed over, any failure is final and the service raises. This is what prevents sending the same message twice.
- One function, `mailing_enabled()`, replaces every "is mail configured?" check. If no transport is configured, or the sender address is missing, mail is off and the test-send action says why. Startup fails only on contradictory configuration that a running instance cannot already have.
- The service is synchronous and raises on failure. Callers that must not block wrap it in a Huey task that reports the outcome, as the workflow `send_email` action does since #4654. A task that swallows the error and reports success is not acceptable. Password reset and invitations stay inline, as today. The reset endpoint keeps its neutral response so it never reveals whether an address exists.
- A "send test email" action for administrators. It sends only to their own address and reports the mailer used and the error, if any.

### Later

- Declaring any number of mailers of any type from the environment, when a customer needs a fallback that is not SMTP.

### Out of scope

- Delivery webhooks, bounce tracking and inbound mail. No new inbound endpoint.
- Templates, i18n and the task queue. Huey stays.

## Transition

Running instances upgrade by pulling a new version. They must not need to touch their configuration, rolling back must be as simple as running the previous image, and no phase adds a migration.

Order of delivery: first the service, the test-send action and OAuth over SMTP, with guides for Microsoft 365 and Google Workspace, before Microsoft disables basic authentication by default. Existing configurations see no change other than failover now covering every message. Then the Graph backend. Then the Later item as demand appears. The first phase is accepted on an end-to-end test against the mailpit container in the compose stack, plus unit tests for failover order and the cases that must not fail over. Its release notes say no action is required.

Django 7.0 removes what 6.1 deprecated: the `EMAIL_*` settings except `DEFAULT_FROM_EMAIL`, `get_connection()`, the `connection` and `fail_silently` arguments, and direct construction of the SMTP backend. After the first phase our code uses none of them. Our environment variables share their spelling with the removed settings but are ours: our settings module reads them and never hands them to Django under those names.

## Security considerations

- New secrets in the environment: an Entra client secret or a Google service account key. Same handling as the SMTP password: environment only, never logged, never exposed through the API.
- On Microsoft 365, a tenant-wide `Mail.Send` or `SMTP.SendAsApp` grant in Entra lets a leaked secret send as any mailbox. The customer guide requires Exchange RBAC for Applications with a scope limited to the sending mailbox and no grant in Entra, since grants from the two systems add up. We cannot verify that the customer did this.
- On Google Workspace, SMTP with OAuth requires the full mail scope and domain-wide delegation, which cannot be limited to one mailbox. A leaked key can read and send as any user in the domain. The guide says this plainly. Customers who cannot accept it use the IP-allowlisted relay instead.
- The fixed transport list prevents loading arbitrary classes from an environment variable. The test-send action is admin-only, own address only and rate limited, so it cannot relay.
- A later mailer can silently carry all traffic when the first is misconfigured. The error log on every failover is the mitigation.

## Alternatives considered

- **SMTP only, pointing Microsoft 365 customers at High Volume Email or a local relay**: rejected. HVE only delivers to internal recipients. A relay moves the problem to the customer.
- **A third-party Graph package, django-msgraphbackend or django-o365**: rejected. Single maintainers for a small amount of credential-handling code.
- **Provider HTTP APIs through django-anymail**: rejected. SMTP with an API key reaches every provider, and what the APIs add, tracking, webhooks and provider-side templates, is outside the product.
- **Configuring mail in the admin UI instead of environment variables**: rejected for now. It puts secrets in the database and changes when configuration takes effect. Revisit if customers ask.
- **A dedicated rescue mailer**: rejected. A special case of an ordered list, limited to one fallback.
- **Failing over on every error**: rejected. It can send a message twice.
- **Queuing every message and letting the task swallow errors**: rejected. That is the bug #4654 fixed.
- **django-post_office or django.tasks**: rejected. Huey already queues, and Django ships no worker.
- **An operator-supplied `MAILERS` dict or backend class path**: rejected. Arbitrary code loading and unsupported combinations.
