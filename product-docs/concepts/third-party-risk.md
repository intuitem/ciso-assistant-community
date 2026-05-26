# Third-party risk

**Third-party risk management** (TPRM) is the discipline of evaluating the security and compliance posture of the vendors, suppliers, and service providers your organisation depends on.

CISO Assistant treats third parties as a first-class concern with their own object graph, separate from internal compliance work.

## Mental model

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

## How the vendor answers the questionnaire

CISO Assistant supports two modes for getting the actual answers back from the vendor, depending on whether the third party is allowed to access your instance.

### Online mode — the representative logs in

This is the default workflow. You create a **representative** on the entity side, the platform issues credentials, and the representative logs into CISO Assistant directly to fill in the questionnaire. Their access is scoped: they only see the entity assessment(s) attached to their entity, and they land in a dedicated **third-party / auditee surface** — a separate route group with its own auditee dashboard, not the rest of your workspace.

This surface is gated by the **`auditee_mode`** [feature flag](../configuration/settings/feature-flags.md), which has to be on for the third-party login flow to be available.

Use this mode when:

- Your instance is reachable from the internet (or from the vendor's network).
- You want live progress visibility — answers land in the database as they're typed, so the dashboard updates in real time.
- You want comments, validation flows, and the full audit trail to apply to the vendor's answers automatically.

> Don't confuse this with the [Assignments / respondent mode](../features/assignments.md) feature — that one is for **internal** users splitting one audit across teammates using the `respondent` role within your own organisation. The third-party flow described here is for **external vendors** answering through the auditee surface.

### Offline mode — Excel exchange via the data wizard

Many organisations don't want to expose their CISO Assistant instance to third parties — for security, network, or contractual reasons. In that case, the platform supports a fully **file-based round trip**:

1. **Export the questionnaire from the framework page.** On the framework backing the entity assessment, use the **Export to Excel** action. You get an `.xlsx` file containing every requirement of the framework, structured so the vendor can fill in the answers, observations, and supporting evidence references in dedicated columns.
2. **Send the file to the vendor.** Email, secure file share, sneakernet — whatever channel your procurement and security policies allow. The vendor opens the spreadsheet in any tool that can edit Excel.
3. **Receive the filled-in file back.** The vendor returns the spreadsheet with their answers populated. No platform access was needed at any point.
4. **Re-import via the data import wizard.** Use the [data import wizard](../configuration/data-import.md) to upload the filled-in spreadsheet. The wizard maps the rows back to the requirement assessments on the existing entity assessment, populating answers, observations, and any other captured columns.

Use this mode when:

- Your instance can't be (or shouldn't be) exposed to the vendor's environment.
- The vendor refuses to log into a third-party platform.
- You want a tangible artefact — the signed-off Excel — as part of the audit record.

Both modes produce the **same internal state** at the end: a populated entity assessment with per-requirement answers and observations. You can mix them within an organisation (online for one vendor, offline for another) or switch a single vendor from one mode to the other mid-cycle if the situation changes.

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
