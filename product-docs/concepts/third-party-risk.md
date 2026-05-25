# Third-party risk

**Third-party risk management** (TPRM) is the discipline of evaluating the security and compliance posture of the vendors, suppliers, and service providers your organisation depends on.

CISO Assistant treats third parties as a first-class concern with their own object graph, separate from internal compliance work.

## Object graph

Four interlocking objects model the third-party landscape:

- **Entity** — a vendor, supplier, or service provider. The unit of organisational identity.
- **Solution** — a specific product or service provided by an entity. An entity can have many solutions.
- **Contract** — the formal agreement covering one or more solutions, with dates, renewal terms, and obligations.
- **Representative** — the person on the entity side who answers questionnaires and signs off on assessments.

## Entity assessment

The actual review of a third party is an **entity assessment**. It can:

- Use a questionnaire — custom, or imported from a library (CAIQ, SIG, …).
- Trigger an internal audit that lives in the entity's domain, so the third party can fill it in directly.
- Capture the residual risk you accept by working with this entity.

## Why a separate model

Treating third parties as a parallel surface — rather than just "another perimeter" — matters because:

- Permissions differ: third-party representatives need restricted access, not full role-assignment privileges in your domain.
- Lifecycle differs: contracts have renewal dates, vendors come and go, but your internal frameworks stay stable.
- Reporting differs: TPRM dashboards aggregate across many entities, not down inside one.

## Related

- [Domains](domains.md)
- [Audits](audits.md)
- [Guide → Third-party risk management](../guides/tprm.md)
- [Vocabulary → Entity / Solution / Contract / Representative / Entity assessment](../introduction/vocabulary.md)
