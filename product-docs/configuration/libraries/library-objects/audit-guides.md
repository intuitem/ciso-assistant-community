---
description: Write your own auditor guide for the Auditor pre-read
---

# Audit guides

{% hint style="warning" %}
Experimental. Audit guides feed the **Auditor pre-read**, available when the experimental features are on.
{% endhint %}

An audit guide says, for each requirement of a framework, what a certification auditor will ask, which records they will request, what they will sample, who they will interview and where audits usually find something. It also orders the requirements into the **Audit sessions** an auditor runs on site. The Auditor pre-read sets this against what you have on file to tell you what is ready and what is not.

CISO Assistant ships a guide for ISO/IEC 27001:2022, written in our own words. You can load your own: a different wording, your certification body's habits, another framework (an internal standard, a sector scheme) or a translation.

## Make your own guide

Audit guides are written in YAML only; the Excel converter does not handle them.

1. Start from the guide we ship, `audit-guide-iso27001-2022.yaml` in the libraries folder of the repository, or from an empty file with the structure below.
2. Give the library and the guide your own `urn`, `ref_id` and `name`, and set `provider` to your organisation's name. A guide whose `provider` is not `intuitem` takes precedence over ours on the same framework.
3. Edit the entries: rewrite questions, add or remove requested records, change who answers, regroup the sessions.
4. Load the file from the libraries page, like any other library.

Keep item ids stable when you edit an existing guide: pairings of evidence with a request, and requests marked **Doesn't apply**, are stored against the guide's URN and the item id. A renumbered request loses them.

{% hint style="info" %}
An AI assistant does this well when you give it the file and the rules on this page: "rewrite the questions of clauses 4 to 10 in our certification body's style, keep every id, `who` within `interviewees`". Check the result loads before sharing it.
{% endhint %}

{% hint style="danger" %}
Do not paste text from the standards or from paid checklists into a guide you publish. Your own instance is your call.
{% endhint %}

## Structure

```yaml
urn: urn:acme:risk:library:audit-guide-iso27001-2022
locale: en
ref_id: acme-audit-guide-iso27001-2022
name: ACME auditor guide for ISO/IEC 27001:2022
version: 1
provider: ACME
packager: ACME
objects:
  audit_guides:
    - urn: urn:acme:risk:audit_guide:iso27001-2022
      ref_id: acme-iso27001-2022
      name: ACME auditor guide for ISO/IEC 27001:2022
      framework: urn:intuitem:risk:framework:iso27001-2022
      entries:
        a.5.18:
          questions:
            - {id: q1, stage: 2, who: [iam, hr], text: "Walk me through a joiner, a mover and a leaver."}
          requests:
            - {id: r1, label: "Access review records, last 2 cycles", kind: record, fresh_days: 200, reference_control: urn:intuitem:risk:function:doc-pol:proc.recertification}
          sampling:
            - {id: s1, min: 5, max: 5, unit: "leavers", population: "last 12 months", method: "compare the HR exit date to the account disable date"}
          interviewees: [iam, hr]
          pitfalls:
            - {id: p1, text: "Reviews done but no record of the revocations they called for"}
      sessions:
        - {id: access, label: "Identity and access management", members: [a.5.15, a.5.18]}
      translations:
        fr:
          name: Guide de l'auditeur ACME pour ISO/IEC 27001:2022
          entries:
            a.5.18:
              q1: "Décrivez-moi une arrivée, une mobilité et un départ."
              r1: "Revues des droits, deux derniers cycles"
              s1: {unit: "départs", population: "12 derniers mois", method: "…"}
          sessions:
            access: {label: "Gestion des identités et des accès"}
```

### The guide

| Field | Meaning |
| --- | --- |
| `urn`<mark style="color:$danger;">*</mark> | The guide's own URN, `urn:<packager>:risk:audit_guide:<identifier>` |
| `ref_id`<mark style="color:$danger;">*</mark> | Identifier |
| `name` <mark style="color:$info;">T</mark> | Name shown in the pre-read |
| `framework`<mark style="color:$danger;">*</mark> | URN of the framework the guide is written for |
| `entries`<mark style="color:$danger;">*</mark> | One entry per requirement, keyed by the last part of the requirement's URN (`a.5.18`, `9.2.1`) |
| `sessions` | The audit sessions, in the order the auditor runs them |
| `translations` | Per language: `name`, then the texts of entries and sessions keyed by item id |

### An entry

| Field | Meaning |
| --- | --- |
| `questions` | `id` (`q1`, `q2`…), `stage` (1 for the document review, 2 on site), `who` (1 to 3 roles from `interviewees`, required), `text` |
| `requests` | `id` (`r1`…), `label`, `kind` (`document`, `record`, `technical` or `observation`), and optionally `fresh_days` and `reference_control` |
| `sampling` | `id` (`s1`…), `min`, `max`, `unit`, and optionally `population`, `method`, `note`. Leave it empty when the auditor only reads documents |
| `interviewees` | Roles among `top`, `ciso`, `risk`, `auditor`, `hr`, `legal`, `dpo`, `proc`, `facilities`, `it_lead`, `iam`, `infra`, `network`, `endpoint`, `service_desk`, `sec_ops`, `dev`, `staff` |
| `pitfalls` | `id` (`p1`…), `text`: where audits usually find something |

Rules the loader checks:
* every item has an id, unique within its entry; never reuse a retired id;
* a question's `stage` is 1 or 2 and its `who` stays within the entry's `interviewees`;
* a request has a `label` and one of the four kinds;
* every session has an `id` and a `members` list.

### What drives the verdicts

* `kind: observation`: something the auditor watches on site; it is never filed as evidence and does not count.
* `fresh_days`: how recent the newest record must be, the cadence plus some slack: 40 (monthly), 100 (quarterly), 200 (half-yearly), 400 (yearly). Leave it out for records sampled from the audit period (leavers, incidents) and one-off records.
* `reference_control`: set it only when the request *is* that item (the policy, the register). Evidence of an applied control with this reference control answers the request automatically, and requests sharing a reference control are one document: pairing it once answers all of them.

### Sessions

Each session lists the entries it covers in `members`; an entry belongs to one session. A session can carry its own `requests` and `pitfalls`, like an opening or closing meeting with no requirement of its own.

## Which guide an audit uses

A guide applies to an audit on its own framework, and to a framework with the same requirement numbering (a licensed copy, a translation): each requirement is matched by its number, falling back to the parent number (`4.2 a)` reads as `4.2`; `A5.1` and `A.05.01` read as `a.5.1`). When only part of the guide lands, the pre-read offers **Apply the guide anyway**.

When several guides fit, a guide written for the audit's own framework wins, yours before ours. Otherwise, the guide whose numbering matches best applies.
