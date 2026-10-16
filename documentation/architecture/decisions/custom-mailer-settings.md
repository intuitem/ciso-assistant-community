# Let administrators configure a custom mailer in the app, behind an environment switch

- Status: Proposed
- Deciders: @nas-tabchiche, @ab-smith

## Context

Hosted customers want their mail sent from their own domain. Today that means we edit their instance's environment by hand, which does not scale and puts their credentials in our hands. [pluggable-mail-transport](pluggable-mail-transport.md) gave us one mail service and an ordered list of mailers built from the environment. What is missing is a way for an administrator to supply that configuration from inside the application.

We do not want every hosted instance to have this ability. It is a service we switch on per customer. On-prem operators own their instance and decide for themselves.

## Decision

We will add a mail settings panel where an administrator configures a primary mailer, an optional second mailer and the sender address, tests the values in the form, and saves. A mailer cannot be saved until its test has succeeded, except through an explicit override for a server that refuses to deliver to the administrator's own address. The configuration is stored in the database. Credentials are written through the API and never read back, as the SSO client secret already is.

The panel exists only when `ENABLE_CUSTOM_MAILER` is true in the environment. It is false by default. When it is false, the panel is hidden, the API refuses reads and writes, and any stored configuration is ignored. We set it on hosted instances at our discretion. On-prem operators set it if they want it.

When the switch is on and the stored configuration is active, it replaces the environment mailers entirely. When nothing is stored, or the configuration is parked with its active flag off, the environment applies as before. The service resolves the active mailers at send time, so a saved change applies to the next message with no restart.

The panel also shows delivery health: per mailer, the last attempt with its time, outcome, and whether failover reached it.

## Consequences

- Mailers live in a table, one row per mailer with a position, plus an active flag for the whole configuration. The fields are what a `MAILERS` entry holds: transport from the fixed list, host, port, TLS mode, username, secret, and for OAuth the grant, token URL, scope and credentials. Delivery health is a second table, one row per mailer updated in place. Both come in the one schema migration this work adds.
- Transports offered in the panel are exactly the transports in the fixed list. Adding a transport adds its fields to the panel and nothing else.
- Access goes through the standard model permissions of the new table, granted to the built-in administrator role and checked like any other permission. No hardcoded administrator check. Every change is audit-logged.
- The test button sends to the administrator's own address with the values currently in the form, without saving them, and reports the mailer used, the mailers skipped and the error, if any. An empty secret field on an existing mailer means "keep the stored secret", for the test as for the save.
- Saving a change emails every other administrator, through the mailer that was active before the change, naming who changed what and when.
- Delivery health is recorded by the service on every send, for environment-configured mailers too. The panel shows it; `send_test_email` prints it for operators without the panel.
- The switch is a kill switch. Turning it off on a hosted instance returns it to our environment mailer immediately, whatever the customer stored. The active flag is the soft equivalent an administrator controls.
- Hosted customers who configure their own mailer get no fallback to our mailer. A message from their domain relayed through our provider fails their DMARC and is rejected.
- Environment variables keep their names and meaning. An instance with the switch off is unchanged by this decision.
- The `MAILERS` setting keeps one entry, our own backend, which reads the active configuration when it opens a connection. Third-party code that sends through Django follows the same configuration without knowing about it.

## Security considerations

- Whoever can change the mail server receives every password reset link the instance sends afterwards and can take over any account. Hence administrator-only permission, audit log, notification of the other administrators, and a switch that defaults to off. Treat it with the same care as the SSO settings.
- The change notification goes through the previous mailer on purpose: the one just replaced cannot suppress it.
- Mail credentials join the SSO client secret and workflow secrets in the database and in its backups. Same handling: write-only through the API, never logged.
- The environment switch sits outside the administrator's reach. A compromised administrator account on a hosted instance cannot enable the panel; only we can.
- Hidden is not disabled. The API checks the switch on every request, not only the frontend.
- A mailer that passed its test can still stop working later. Delivery health makes that visible without waiting for a user to report a missing email.

## Alternatives considered

- **Keep editing hosted instances by hand**: rejected. It does not scale and we hold customer credentials.
- **Always-on panel, no switch**: rejected. We want to decide per hosted customer, and the switch costs nothing on-prem.
- **A database feature flag instead of an environment variable**: rejected. The switch must be out of reach of the instance's own administrators.
- **Store the configuration in the `GlobalSettings` JSON blob like SSO**: rejected. Ordered mailers with their own secrets want validation, per-row audit logging and write-only handling that a blob does not give.
- **Fall back to our mailer when the customer's is down**: rejected. It fails the customer's domain authentication.
- **Allow saving an untested mailer**: rejected. A typo silently breaks password reset for every user; the test is cheap and the override covers the one legitimate case.
- **A hardcoded administrator check**: rejected. Standard model permissions keep the RBAC model uniform.
- **Audit log only, no notification on change**: rejected. Audit logs are read after the fact; the risk is a quiet takeover of the password reset channel.
