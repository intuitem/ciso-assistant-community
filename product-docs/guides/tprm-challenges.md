---
description: Common configuration pitfalls when running entity assessments, and where to fix them.
---
# Common TPRM pitfalls

This page collects the recurring ones and points at the exact setting that resolves each.

The reference walkthrough for the happy path lives at [Third-Party Risk Management](tprm.md); the underlying object model is described in [Third-party risk](../concepts/third-party-risk.md).

## The assignment never starts

**Symptoms.** You sent the questionnaire to a representative, but the entity assessment progress stays at zero. The representative either gets no email, lands on an empty respondent view, or sees a blank questionnaire.

Walk through this checklist in order:

1. **Assignment/Respondent mode feature flag is off.** Without it, the external respondent surface is not exposed at all. Toggle it from **Extra → Settings → [Feature flags](../configuration/settings/feature-flags.md)** **→ Assignment/Respondent mode**
2. **The representative has no user account.** When you create a representative, the **Create user** checkbox is what actually provisions credentials. Without it, the representative is only a contact record — no one to log in or be assigned questions. Re-open the representative form and tick the box, or recreate the representative.
3. **The entity assessment has no audit.** The questionnaire lives on the audit attached to the assessment. If **Create audit** was not ticked at assessment creation, there is no questionnaire to send. Either edit the assessment and attach an audit using an existing framework, or recreate it with **Create audit** checked.
4. **The auditee-assessment is still in Draft.** If the assignments never transitioned to **In progress** after you clicked **Send questionnaire**, the invitation mail almost certainly failed to send. See [the mailer section below](#the-mailer-is-not-configured) to fix SMTP, then retry. In parallel, you can start the assessment manually from the underlying audit by flipping the assignment statuses yourself — this follows the same mechanics as the internal [respondent mode](../features/assignments.md), so the same workflow applies once you open the audit's **Assignments** panel.
5. **Field visibility hides the requirements from the respondent.** If every assessable field is set to **Auditor only** or **Hidden**, the respondent loads the audit and sees nothing actionable. See [Field visibility on the entity-assessment audit](#field-visibility-on-the-entity-assessment-audit).

If all five are clean and the assignment still does not progress, check the backend logs for mailer errors and confirm the representative's email is reachable from your network.

## The mailer is not configured

**Symptoms.** Representatives report they never received the invitation. Password resets from the UI also fail silently. The backend logs contain SMTP errors, or nothing at all because no SMTP host is set.

CISO Assistant sends every transactional email — invitations, password resets, notifications — through a single SMTP configuration. There is **no in-app form** for this: it lives entirely in environment variables on the backend container.

Go to [Setting up mailer](../installation/mailer.md) for the full reference. The minimum to set is:

```bash
EMAIL_HOST=smtp.example.com
EMAIL_PORT=465
EMAIL_HOST_USER=noreply@example.com
EMAIL_HOST_PASSWORD=<secret>
DEFAULT_FROM_EMAIL=noreply@example.com
EMAIL_USE_SSL=True       # or EMAIL_USE_TLS=True for STARTTLS on 587
```

Pick **either** `EMAIL_USE_SSL` **or** `EMAIL_USE_TLS`, never both. After changing variables, restart the backend container.

{% hint style="warning" %}
On backend 3.16+ the container is rootless and read-only, and TLS verification is strict. A self-signed or internally issued CA must be mounted via `SSL_CERT_FILE` — the old `update-ca-certificates` recipe no longer works. See the [TLS section of the mailer page](../installation/mailer.md#tls-certificate-requirements-3.16) for the certificate extensions required (BasicConstraints, KeyUsage, AKI).
{% endhint %}

To verify, trigger a password reset from the UI and watch the backend logs. A clean send means TPRM invitations will also go through.

## Field visibility on the entity-assessment audit

**Symptoms.** The representative can log in, but the questionnaire shows columns they should not see (internal scoring, draft observations) or hides columns they need to fill (Result, Answers).

Field visibility is **not** configured on the entity assessment itself — it lives on the **audit** attached to the assessment. The assessment is the wrapper; the audit is where requirements and their per-field visibility rules sit.

To reach it:

1. Open the entity assessment.
2. Click through to its linked audit.
3. **Edit** the audit and open the **More** dropdown.
4. The **Field visibility** panel is the second block, with one pill per field.

Each field can be set to one of three states:

| Pill                                       | Auditor (you) | Respondent (third party) |
| ------------------------------------------ | ------------- | ------------------------ |
| **Auditor + Respondent** _(green)_ | edit          | edit                     |
| **Auditor only** _(amber)_         | edit          | hidden                   |
| **Hidden** _(rose)_                | hidden        | hidden                   |

For a third-party questionnaire you typically want:

- **Answers**, **Result**, **Observation**, **Applied controls**, **Evidences** → _Auditor + Respondent_ so the vendor can fill them in.
- **Status**, **Extended result** → _Auditor only_ so the vendor cannot self-assign a final lifecycle state or qualifier.
- **Score**, **Documentation score** → _Hidden_ (the default), unless you explicitly want the vendor to score themselves.
- **Comments** → flip to _Auditor only_ on sensitive engagements, so internal back-and-forth is not exposed to the vendor.

Parent / child constraints are enforced live: **Documentation score** cannot be more permissive than **Score**, and **Extended result** cannot be more permissive than **Result**. Lowering a parent auto-clamps the child.

Defaults cascade: audit override → framework default → platform default. If you keep getting the same wrong defaults across new assessments, fix it on the **framework** (Authoring → Framework → field visibility) so every audit spawned from it starts correct.

The full reference is in [Customize your audit → Field visibility](customize-audit.md#field-visibility).

## Related

- [Third-Party Risk Management](tprm.md) — the happy-path walkthrough.
- [Third-party risk](../concepts/third-party-risk.md) — the underlying object model and the online vs offline modes.
- [Feature flags](../configuration/settings/feature-flags.md) — `auditee_mode`, `tprm`, `contracts`.
- [Setting up mailer](../installation/mailer.md) — SMTP and TLS reference.
- [Customize your audit](customize-audit.md) — field visibility, scoring, lifecycle.
