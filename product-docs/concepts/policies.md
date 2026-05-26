# Policies

A **policy** is a specific type of applied control: a document describing what is expected from some part of your stakeholders — an acceptable-use policy, a password policy, a data-classification policy, an incident-response procedure, anything that defines _how things should be done_.

Because policies are applied controls under the hood, they inherit the full applied-control machinery: they live in a domain, have an assignee and a status, link to the requirements they satisfy, and carry evidence.

## Why give policies their own page

Policies are central to most compliance frameworks — almost every requirement expects a documented policy as part of the substantiating artifacts. Pulling policies onto a dedicated page lets you:

- Maintain the catalogue of published documents independently of the broader action plan.
- Track policy review and approval cycles separately from operational controls.
- Surface policies by domain when responding to audit requests or external reviews.

The Policies page in the platform is a filtered view of applied controls where the type is _policy_; everything you can do to an applied control, you can do to a policy.

## Authoring options

Policies can come from either side of the divide:

- **Author in CISO Assistant.** Each policy can carry one or more **managed documents** — versioned documents tracked in-platform through a draft → in-review → validated → published → deprecated lifecycle. Useful when you want the policy text to live where the rest of the GRC programme lives, with revision history and approval workflow attached.
- **Attach existing documents.** If your policies already live in Confluence, SharePoint, a DMS, or anywhere else, the policy entry can point at the external location via a link and carry evidence files (signed PDF, last-approved revision) without duplicating the source-of-truth.

Both paths are first-class — you can mix them across an organisation, or even across policies in the same domain. The applied-control machinery (assignee, status, linked requirements, evidence) is the same either way.

## Versioning, history, and diff

For policies authored in CISO Assistant, every change produces a new **revision** of the managed document rather than overwriting the previous text. Each revision carries:

- A monotonically increasing **version number** (`v1`, `v2`, …).
- A revision **status** (draft / in review / change requested / validated / published / deprecated).
- A timestamp, the actor who edited it, and the content at that point in time.

The full revision list is reachable from the **version history** sidebar on the document page — you can switch between revisions to read any past version exactly as it was published.

### Diff between revisions

Two diff views help reviewers and approvers see what actually changed:

- **Diff between two revisions** — pick a "from" revision and a "to" revision in the history sidebar and the platform renders the textual differences between them. Useful for periodic reviews ("what changed between v3 and v6?") and for the approval workflow ("show me the delta the requester is asking me to validate").
- **Edit diff (within a revision)** — while a draft is being worked on, the platform also tracks the diff between the _last loaded state_ and the _current edits_ in the editor. This lets the author see exactly what they're about to commit before they save the increment.

The diff is computed on the document content itself — it's not a binary file diff, so it works well for the plain-text or Markdown policies typically authored in-platform. For policies attached as external files (PDF, DOCX, etc.), version history is preserved through evidence revisions, but the inline diff view is not available.

## Lifecycle

Policies have their own lifecycle — drafting, review, approval, publication, periodic review, retirement. The platform tracks these states through the standard applied-control status field and the supporting evidence on each policy entry. When authoring in-platform, the managed-document revision states (draft, in review, validated, published, deprecated) provide a finer-grained workflow on top.

## Related

- [Applied controls](applied-controls.md)
- [Audits](audits.md)
- [Evidence](evidence.md)
- [Vocabulary → Policy](../introduction/vocabulary.md)
