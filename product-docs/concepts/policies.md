# Policies

A **policy** is a specific type of applied control: a document describing what is expected from some part of your stakeholders — an acceptable-use policy, a password policy, a data-classification policy, an incident-response procedure, anything that defines _how things should be done_.

Because policies are applied controls under the hood, they inherit the full applied-control machinery: they live in a domain, have an owner and a status, link to the requirements they satisfy, and carry evidence.

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

Both paths are first-class — you can mix them across an organisation, or even across policies in the same domain. The applied-control machinery (owner, status, linked requirements, evidence) is the same either way.

## Lifecycle

Policies have their own lifecycle — drafting, review, approval, publication, periodic review, retirement. The platform tracks these states through the standard applied-control status field and the supporting evidence on each policy entry. When authoring in-platform, the managed-document revision states (draft, in review, validated, published, deprecated) provide a finer-grained workflow on top.

## Related

- [Applied controls](applied-controls.md)
- [Audits](audits.md)
- [Evidence](evidence.md)
- [Vocabulary → Policy](../introduction/vocabulary.md)
