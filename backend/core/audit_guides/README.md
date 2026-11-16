# Audit guides (experimental)

Per-requirement entries of what a certification auditor will ask, request,
sample and who they will interview. Keyed by the requirement node URN suffix
of the framework named in `framework_urn`. Served by
`GET /api/compliance-assessments/{id}/auditor_preread/`.

All wording is our own. Never paste text from the ISO standards (27001,
27002, 27007, 27008) or from third-party checklists.

```yaml
framework_urn: urn:intuitem:risk:framework:iso27001-2022
entries:
  a.5.18:                      # URN suffix of the requirement node
    questions:
      - {id: q1, stage: 2, text: "Walk me through a joiner, a mover and a leaver."}
    requests:
      - {id: r1, label: "Access review records, last 2 cycles", kind: record, fresh_days: 200, reference_control: urn:intuitem:risk:function:doc-pol:proc.recertification}
    sampling:
      - {min: 5, max: 5, unit: "leavers", population: "last 12 months", method: "compare HR exit date to account disable date"}
    interviewees: [iam, hr]
    pitfalls:
      - {id: p1, text: "Reviews done but no record of revocations acted on"}
```

- `id`: `q<n>`, `r<n>`, `p<n>`, unique within the entry. Never renumber or
  reuse a retired id: translations and evidence links key on it.
- `stage`: 1 (documentation review) or 2 (implementation, sampling).
- `kind`: document | record | technical | observation.
- `observation`: seen on site, never a linked evidence, so not counted in readiness.
- `fresh_days`: records/technical only, one of 40 (monthly), 100 (quarterly),
  200 (half-yearly), 400 (yearly): the cadence plus slack. Leave it out for
  event-driven records sampled from the audit period (leavers, incidents) and
  one-off records (signed at hire). Current-state exports and running trackers get 400.
- `reference_control`: a URN from the key reference controls library
  (`key-reference-controls.yaml`), only when the request *is* that item (the
  policy, the register, the capability), not a record about it. Requests
  sharing one are the same document asked by several requirements. Never the
  one-to-one Annex A reference controls (`doc-pol:a.5.18`): every request of
  the control would share it.
- `sampling`: `[]` when the auditor only reviews documents; one row per
  population sampled, `note` for qualifiers ("including the most severe").
- `interviewees`: top, ciso, risk, auditor, hr, legal, dpo, proc, facilities, it_lead, iam, infra, network, endpoint, service_desk, sec_ops, dev, staff.
- Every entry has a Stage 1 question except clauses only checked in operation (5.1, 10.x).

`sessions.yaml` orders the entries into Stage 2 sessions, the way an auditor
runs the days: by topic, each session with the same people. Every entry
belongs to exactly one session (tested). A session may carry its own
`requests` and `pitfalls`, as the opening meeting does.

Findings from earlier audits (Stage 1, internal audit) come from the
findings assessments: any `Finding` linked to the requirement, or to a
requirement assessment of any audit on the same framework. An open one at
medium severity or above reads as a potential nonconformity (gap); below, as
a point to watch (weak).

## Target (decided 2026-11-16, not implemented yet)

- Shipped as an **audit guide** library (object type `audit_guides`, model
  `AuditGuide`, one entry per requirement) that depends on the framework
  library and is versioned on its own.
- Matching is automatic only: an evidence answers a request when it comes through
  an applied control whose reference control is the request's. Per-request
  freshness and coverage replace the count and tightest-window heuristics.
  Manual evidence-to-request links come later, keyed by request `id`.
- `translations: {<locale>: {questions|requests|pitfalls: {<id>: text}, sampling: {<unit>: text}}}`,
  keyed by id, never by position.
