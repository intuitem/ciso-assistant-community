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
- `fresh_days`: optional, records/technical only: how old the newest one may be.
- `sampling`: null when the auditor only reviews documents.
- `interviewees`: top, ciso, risk, auditor, hr, legal, dpo, proc, facilities, it_lead, iam, infra, network, endpoint, service_desk, sec_ops, dev, staff.
