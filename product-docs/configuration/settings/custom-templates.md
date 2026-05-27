{% hint style="info" %}
Available on the PRO plan.
{% endhint %}

# Custom templates

Custom templates let you replace the default content CISO Assistant uses for outbound emails and for document exports.

Two template types live under this setting:

- **Email templates** — the body and subject of system-generated emails (notifications, invitations, password reset, …).
- **Word templates** — `.docx` files used as the visual skin for document exports (audit reports, risk-treatment plans, BIA outputs).

## Template key and language

Every template is identified by two fields:

- **Template key** — a stable identifier for what the template represents (e.g. `audit_completion_notification`, `audit_report_export`). The platform looks up the active template by key when the relevant action fires.
- **Language** — the locale the template applies to. The platform falls back to the instance's default language if no template for the user's locale is present.

A template is only used when its `is_active` flag is on, which lets you stage a draft alongside the live version and flip the switch when ready.

## Email templates

Each email template carries a **subject** and a **body**. Body content supports the same templating variables as the default emails — use the in-app preview to inspect the variables available for a given key.

## Word templates

Each Word template is an uploaded `.docx` file containing styled placeholders. The platform substitutes the dynamic content (assessment data, scores, evidence list) when generating the export.

## Operational notes

- Editing a template doesn't retroactively change documents that have already been exported.
- Inactive templates remain in the database for audit-trail purposes.
