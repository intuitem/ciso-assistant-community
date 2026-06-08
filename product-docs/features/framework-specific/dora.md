---
description: Register of Information and structured incident reports for DORA compliance
---

# DORA

The EU [Digital Operational Resilience Act](https://www.eiopa.europa.eu/digital-operational-resilience-act-dora_en) (DORA) imposes two specific reporting obligations that CISO Assistant produces out of the box: the **Register of Information** on ICT third-party arrangements, and structured **major incident reports** filed with the supervisory authority.

## Register of Information (RoI)

DORA Article 28(3) requires regulated financial entities to maintain — and periodically submit — a register listing every ICT third-party service provider, the services consumed from each, the supporting contracts, and a number of classification fields.

CISO Assistant builds this register from the entities, solutions, and contracts you already track in the **third-party risk** module:

1. Open **Reports** → **DORA Register of Information**.
2. The page **lints** your data first — it flags missing fields the RoI requires (LEI codes, criticality classifications, contractual fields, …) so you can fix them before exporting.
3. Once the lint is clean, download the RoI in the official ESMA template format.

The lint pass is the part that pays for itself: filing an RoI with missing required fields means it gets rejected and you redo the work. Running the lint while the data is fresh in your hands is much cheaper.

## DORA incident reports

DORA Article 19 requires regulated entities to report **major ICT-related incidents** to the competent authority on a defined timeline (initial notification, intermediate report, final report). The notification template is prescriptive — specific fields, specific formats.

CISO Assistant ships a dedicated **DORA incident report** object:

- Created from an existing [incident](../../concepts/incidents.md), inheriting the operational data already captured there (timing, scope, affected entities).
- The form mirrors the official DORA fields and validates required content per report phase (initial, intermediate, final).
- Each report can be exported as JSON aligned with the authority's submission schema.
- New report phases can be created from an existing one (`new?from=…`), inheriting the prior phase's content as the starting point — the typical incident report grows over time as the picture clarifies.

The incident detail page links to its DORA reports; the DORA reports page links back to the source incident.

## Related

- [DORA on the EIOPA website](https://www.eiopa.europa.eu/digital-operational-resilience-act-dora_en)
- [Incidents concept](../../concepts/incidents.md)
- [Third-party risk concept](../../concepts/third-party-risk.md)
