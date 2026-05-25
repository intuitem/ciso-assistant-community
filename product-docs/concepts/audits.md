# Audits

> _Draft — placeholder._

An **audit** is the evaluation of a perimeter against a framework. It produces a per-requirement view of status, score, evidence, and the applied controls that substantiate each requirement.

Because applied controls are decoupled from compliance requirements, a single set of controls can be evaluated against many frameworks in parallel without re-doing the work.

## What this page should cover

- The audit lifecycle: planned → in progress → in review → done.
- Requirement assessments, their statuses and scoring methods.
- How evidence and applied controls hang off requirement assessments.
- Mapping libraries: how a single audit can be projected onto another framework via a mapping.
- The auditee role and read-only views for external auditors.

## For users

> _Draft._ Creating an audit from a framework; assigning requirements to actors; scoring; attaching evidence; reviewing; exporting; using mappings to derive a sibling audit.

## For implementers

> _Draft._ Internally an audit is a `ComplianceAssessment`. Related models: `RequirementAssessment`, `RequirementAssignment`, `RequirementMappingSet`. The auditee filtering pattern in `backend/core/views.py`. Tree, donut, and global-score endpoints.

## Related

- [Applied controls](applied-controls.md)
- [Perimeters](perimeters.md)
- [Vocabulary → Audit / Requirement / Evidence](../vocabulary.md)
