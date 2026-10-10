# Let administrators configure a custom mailer in the app, behind an environment switch

- Status: Proposed
- Deciders: @nas-tabchiche, @ab-smith

## Context

Hosted customers want their mail sent from their own domain. Today that means we edit their instance's environment by hand, which does not scale and puts their credentials in our hands. [pluggable-mail-transport](pluggable-mail-transport.md) gave us one mail service and an ordered list of mailers built from the environment. What is missing is a way for an administrator to supply that configuration from inside the application.

We do not want every hosted instance to have this ability. It is a service we switch on per customer. On-prem operators own their instance and decide for themselves.

## Decision

We will add a mail settings panel where a global administrator configures a primary mailer, an optional second mailer, and the sender address, tests them, and saves. The configuration is stored in the database. Credentials are written through the API and never read back, as the SSO client secret already is.

The panel exists only when `ENABLE_CUSTOM_MAILER` is true in the environment. It is false by default. When it is false, the panel is hidden, the API refuses reads and writes, and any stored configuration is ignored. We set it on hosted instances at our discretion. On-prem operators set it if they want it.

When the switch is on and a configuration is stored, it replaces the environment mailers entirely. When nothing is stored, the environment applies as before. The service resolves the active mailers at send time, so a saved change applies to the next message with no restart.

## Consequences

- Mailers live in a table, one row per mailer with a position. The fields are what a `MAILERS` entry holds: transport from the fixed list, host, port, TLS mode, username, secret. This is one schema migration, the only one this work adds.
- Transports offered in the panel are exactly the transports in the fixed list, plain SMTP today, OAuth over SMTP when it ships. Adding a transport adds its fields to the panel and nothing else.
- Only global administrators can read or change mail settings. Every change is audit-logged. The test button sends to the administrator's own address and reports the mailer used and the error, if any.
- The switch is a kill switch. Turning it off on a hosted instance returns that instance to our environment mailer immediately, whatever the customer stored.
- Hosted customers who configure their own mailer get no fallback to our mailer. A message from their domain relayed through our provider fails their DMARC and is rejected. Their second mailer, if any, is theirs too.
- Environment variables keep their names and meaning. An instance with the switch off is unchanged by this decision.
- The `MAILERS` setting keeps one entry, our own backend, which reads the active configuration when it opens a connection. Third-party code that sends through Django follows the same configuration without knowing about it.

## Security considerations

- Whoever can change the mail server receives every password reset link the instance sends afterwards and can take over any account. This is why the panel is restricted to global administrators, every change is audit-logged, and the switch defaults to off. Treat it with the same care as the SSO settings.
- Mail credentials join the SSO client secret and workflow secrets in the database and in its backups. Same handling: write-only through the API, never logged.
- The environment switch sits outside the administrator's reach. A compromised administrator account on a hosted instance cannot enable the panel; only we can.
- Hidden is not disabled. The API checks the switch on every request, not only the frontend.

## Alternatives considered

- **Keep editing hosted instances by hand**: rejected. It does not scale and we hold customer credentials.
- **Always-on panel, no switch**: rejected. We want to decide per hosted customer, and the switch costs nothing on-prem.
- **A database feature flag instead of an environment variable**: rejected. The switch must be out of reach of the instance's own administrators.
- **Store the configuration in the `GlobalSettings` JSON blob like SSO**: rejected. Two ordered mailers with their own secrets want validation, per-row audit logging and write-only handling that a blob does not give.
- **Fall back to our mailer when the customer's is down**: rejected. It fails the customer's domain authentication and lands in spam or is rejected.
