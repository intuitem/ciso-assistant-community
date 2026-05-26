# Settings

The **Settings** page in CISO Assistant is where instance-wide configuration lives — the dials and switches that affect everyone using the platform, regardless of which domain or perimeter they're in.

Settings are grouped into the following categories:

- **[General settings](general.md)** — display preferences, default language, currency and daily rate, AI/LLM provider configuration, retention defaults, and a handful of behavioural toggles (self-validation, MFA enforcement, external-link warnings).
- **[Feature flags](feature-flags.md)** — toggles that turn whole product areas on or off. Use these to tailor the UI to what your team actually needs and to keep advanced or experimental capabilities out of sight until you want them.
- **[Vulnerability SLA policy](vulnerability-sla.md)** — the remediation deadlines (in days) that apply to vulnerabilities by severity, and the anchor date used to compute the clock.
- **[Security intelligence feeds](sec-intel-feeds.md)** — switches for the optional external feeds (KEV, EPSS, NVD enrichment) and the network timeout the platform uses when reaching them.
- **[Branding](branding.md)** _(PRO)_ — replace the default logo, favicon, and client name with your organisation's identity.
- **[Custom templates](custom-templates.md)** _(PRO)_ — override the subject and body of system emails, and the `.docx` templates used for document exports.

## Permissions

Editing settings requires the `change_globalsettings` permission. In practice, this means a Domain Manager on the global domain or an equivalent custom role.

## Scope

Settings on this page are **global** — they apply to the whole instance. Domain-level overrides aren't available at this layer; if you need per-domain behaviour, look at the relevant domain or perimeter's own settings.
