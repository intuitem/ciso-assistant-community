{% hint style="info" %}
Available on the PRO plan.
{% endhint %}

# Custom templates

Custom templates let you replace the default content CISO Assistant uses for outbound emails and for document exports.

{% hint style="warning" %}
**Administrators only.** Creating, editing and deleting custom templates is restricted to users with the **Administrator** role. Templates control the wording of system emails and the body of exported documents, so a malicious or careless template could mislead recipients (e.g. a forged password-reset email) or embed inappropriate content in official exports.

Word templates carry additional risk:

- **Template injection** — `.docx` templates are rendered with a Jinja2-based engine. A crafted template can contain expressions that are evaluated on the server, which an attacker could abuse to read data or run unintended logic during export (server-side template injection).
- **Malicious macros** — `.docx` files can embed VBA macros that execute on the machine of whoever opens the exported document. A booby-trapped template effectively ships malware to every report recipient.

Keep this permission limited to trusted administrators, only upload templates from sources you control, and review any template before activating it.
{% endhint %}

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
