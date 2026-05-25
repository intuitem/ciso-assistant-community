# Project management

The **project-management module** brings PMBOK-style planning into CISO Assistant: a structured way to organise complex, multi-stakeholder initiatives — go-lives, accreditations, transformation programmes — alongside the compliance and risk work they drive.

It's the newest concept in the platform, and the object graph will continue to evolve.

## Object graph

- **Project** — a planned initiative with deliverables, milestones, and a target completion. The unit of work.
- **Accreditation** — a formal authorisation that a system, environment, or product has met security and compliance requirements. Often the gate a project pushes towards.
- **Responsibility matrix** — a RACI-style assignment of actors to activities, attached to a project or to an accreditation flow.
- **Generic collection** — a flexible grouping object: a "bag" of related items that doesn't fit a more specific schema.

## Where it fits

Project objects don't replace [Perimeters](perimeters.md) — they sit alongside. Use a perimeter to define the _scope of assessment_; use a project to plan the _work needed to bring that scope into compliance_ or through an accreditation.

A single project typically references many perimeters, audits, applied controls, and findings assessments — it's the cross-cutting view the security organisation works against day-to-day.

## Disambiguating "project"

In older CISO Assistant documentation, "Project" used to be the name for what is now called a [Perimeter](perimeters.md). The legacy term has been retired everywhere; the **Project** described here is the new project-management object.

## Related

- [Perimeters](perimeters.md)
- [Vocabulary → Project / Accreditation / Responsibility matrix / Generic collection](../introduction/vocabulary.md)
