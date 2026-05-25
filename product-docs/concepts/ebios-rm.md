# EBIOS RM

**EBIOS RM** (_Expression des Besoins et Identification des Objectifs de Sécurité — Risk Manager_) is the structured risk-management method published by the French national cybersecurity agency, [ANSSI](https://cyber.gouv.fr/en/ebios-risk-manager).

CISO Assistant supports EBIOS RM natively, with a dedicated object graph rather than forcing the method into a generic risk-assessment shape.

## The five workshops

EBIOS RM organises a study around five workshops:

1. **Scope and security baseline** — define the studied system, its mission, and the regulations it must comply with.
2. **Risk origins and target objectives** — identify _who_ might attack and _what_ they want (the **RO/TO couples**).
3. **Strategic scenarios** — model attack paths through stakeholders to reach target objectives.
4. **Operational scenarios** — drop into technical detail: kill chains, attacker techniques, supporting assets touched.
5. **Risk treatment** — score residual risk and plan the action plan.

## Object graph

An EBIOS RM **study** owns the following objects:

- **Feared events** — undesirable outcomes on primary assets (workshop 1).
- **Stakeholders** — internal and external parties evaluated for trust and dependency (workshop 1).
- **RO/TO couples** — Risk Origin paired with Target Objective (workshop 2).
- **Strategic scenarios** — high-level "what" of an attack (workshop 3).
- **Operational scenarios** — detailed "how" of an attack, made of **kill chains**, **operating modes**, and **elementary actions** (workshop 4).

The treatment phase reuses the platform's standard objects — applied controls, evidence, residual risk.

## Mapping to qualitative risk

EBIOS RM scenarios sit alongside qualitative risk scenarios in the same risk register: both contribute to the residual-risk picture for a perimeter, and both can be treated with the same applied controls.

## Related

- [Risk assessments](risk-assessments.md)
- [Quantitative risk studies](quantitative-risk-studies.md)
- [Use case → EBIOS RM study](../use-cases/ebios-rm.md)
- [Vocabulary → EBIOS RM and related terms](../introduction/vocabulary.md)
