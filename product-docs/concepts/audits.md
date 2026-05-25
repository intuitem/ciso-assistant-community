# Audits

An **audit** is the evaluation of a perimeter against a framework. It produces a per-requirement view of status, score, evidence, and the applied controls that substantiate each requirement.

Because applied controls are decoupled from compliance requirements, a single set of controls can be evaluated against many frameworks in parallel without re-doing the work.

## Framework

The fundamental input to an audit is a **framework** — a published standard such as ISO/IEC 27001:2022 or NIST CSF. Frameworks ship as YAML libraries. If you can't find one that fits your needs, you can build your own and import it.

## Audit

An audit assesses compliance against the chosen framework. Each requirement carries one of the following statuses:

- **To do**
- **In progress**
- **Non compliant**
- **Partially compliant**
- **Compliant**
- **Not applicable**

The evaluation of a single requirement inside an audit is called a **requirement assessment**.

## Evidence

Evidence justifies the status of a compliance requirement or proves that an applied control has been implemented. It can be a description, a link, or an uploaded file, and it can be attached to any number of applied controls or requirement assessments.

## Related

- [Applied controls](applied-controls.md)
- [Findings assessments](findings-assessments.md)
- [Perimeters](perimeters.md)
- [Vocabulary → Audit / Requirement / Evidence](../introduction/vocabulary.md)
