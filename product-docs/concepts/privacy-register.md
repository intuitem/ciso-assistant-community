# Privacy register

A **privacy register** is the catalogue of personal-data processing activities the organisation carries out — required by GDPR and equivalent regulations as the foundation of accountable data handling.

CISO Assistant models the register as a graph of typed objects so it stays queryable, auditable, and reusable across audits.

## Mental model

- **Processing** — an activity that operates on personal data (collect, store, transfer, delete). The central object.
- **Purpose** — the lawful reason a processing exists. Each processing has at least one purpose.
- **Personal data** — what is being processed (name, email, location, health record, biometric, …), with categories that map to GDPR sensitivity classes.
- **Data subject** — the kind of individual the data refers to (employee, customer, prospect, …).
- **Data recipient** — the internal teams or external parties that receive the data.
- **Data contractor** — third parties that process data on your behalf — a TPRM entity surfaced here with a privacy-specific lens.
- **Data transfer** — flows of data to entities outside the original jurisdiction.

## Event objects

Privacy operations also need to record events as they happen:

- **Right requests** — data-subject requests under GDPR (access, rectification, erasure, portability) and the organisation's response.
- **Data breaches** — incidents affecting personal data, with the notification clock and authority correspondence.

## How it ties into the rest of the platform

- A privacy register lives in a **domain** with its own RBAC scoping — typically a DPO-led folder.
- Findings from GDPR audits surface in the register as actions on processings.
- Data contractors cross-reference TPRM entities, so a sub-processor's security review feeds both worlds.

## Related

- [Domains](domains.md)
- [Third-party risk](third-party-risk.md)
- [Vocabulary → Processing / Personal data / Purpose / Right request / Data breach](../introduction/vocabulary.md)
