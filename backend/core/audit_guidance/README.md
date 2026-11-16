# Audit guidance (experimental)

Per-requirement hints of what a certification auditor will ask, request,
sample and who they will interview. Keyed by the requirement node URN suffix
of the framework named in `framework_urn`. Served by
`GET /api/compliance-assessments/{id}/auditor_preread/`.

All wording is our own. Never paste text from the ISO standards (27001,
27002, 27007, 27008) or from third-party checklists.

```yaml
framework_urn: urn:intuitem:risk:framework:iso27001-2022
guidance:
  a.5.18:                      # URN suffix of the requirement node
    questions:
      - {stage: 2, text: "Walk me through a joiner, a mover and a leaver."}
    requests:
      - {label: "Access review records, last 2 cycles", kind: record, fresh_days: 200}
    sampling: {size: "5 leavers + 5 movers", population: "last 12 months", method: "compare HR exit date to account disable date"}
    interviewees: [iam, hr]
    pitfalls:
      - "Reviews done but no record of revocations acted on"
```

- `stage`: 1 (documentation review) or 2 (implementation, sampling).
- `kind`: document | record | technical | observation.
- `fresh_days`: records/technical only, one of 40 (monthly), 100 (quarterly),
  200 (half-yearly), 400 (yearly): the cadence plus slack. Leave it out for
  event-driven records sampled from the audit period (leavers, incidents) and
  one-off records (signed at hire). Current-state exports and running trackers get 400.
- `observation`: seen on site, never a linked evidence, so not counted in readiness.
- Every entry has a Stage 1 question except clauses only checked in operation (5.1, 10.x).
- `sampling`: null when the auditor only reviews documents.
- `interviewees`: top, ciso, risk, auditor, hr, legal, dpo, proc, facilities, it_lead, iam, infra, network, endpoint, service_desk, sec_ops, dev, staff.

## Target schema (decided 2026-11-16, not implemented yet)

- Shipped as an **audit guide** library (object type `audit_guides`, model
  `AuditGuide`, one entry per requirement) that depends on the framework library and
  holds only guidance (new library object type), versioned on its own.
- Every question, request and pitfall gets an `id`, stable within its requirement.
- `requests[].reference_control`: optional URN from the key reference controls
  library (doc-pol). The request list merges requests sharing one; missing
  shared items (internal audit report, pentest report...) are added there.
- Matching is automatic only: an evidence answers a request when it comes through
  an applied control whose reference control is the request's. Per-request
  freshness and coverage replace the count and tightest-window heuristics.
  Manual evidence-to-request links come later, keyed by request `id`.
- `sampling` becomes a list of `{min, max, unit, population, method}` rows.
- `translations: {<locale>: {questions|requests|pitfalls: {<id>: text}, sampling: {<unit>: text}}}`,
  keyed by id, never by position.
