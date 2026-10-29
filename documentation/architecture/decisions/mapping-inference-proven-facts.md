# Infer mapped compliance from what each link proves

- Status: Proposed
- Date: 2026-10-29
- Deciders: @eric-intuitem

## Context

The mapping engine infers the compliance (`result`) of a target requirement from source assessments, through the links of a requirement mapping set. A link's relationship compares the source with the target: `equal`, `superset` (the source contains the target), `subset` (the source is part of the target) or `intersect`. Several links can reach one target. The inferred results pre-fill an audit created from a baseline in another framework, feed *Map from an audit* ([audit-mapping](../../audit-mapping.md)), and give the compliance distribution of each framework an audit can be mapped to.

The engine kept the most restrictive result over all links, capping a compliant or partially compliant source on a `subset` or `intersect` link at partially compliant, and some paths depended on the order of the links. The most restrictive result misreads consistent evidence: a target with one compliant and one non-compliant subset is non-compliant although part of it is met; a partially compliant superset makes the target partially compliant although its met part may lie entirely outside the target; a compliant `equal` link next to a `not_assessed` partial one gives `not_assessed`.

Some inputs contradict themselves. `A.12.1.2 —equal→ A.8.32` compliant with `A.14.2.2 —subset→ A.8.32` partially compliant (ISO 27001:2013 to 2022) says that all of A.8.32 is met and that part of it is not. No rule settles that; a rule only picks which source to believe. Mapping relationships are approximations, so such inputs will occur.

## Decision

We will infer a target's compliance from the facts its links prove about it, reading compliant as all of the requirement met, partially compliant as some of it met and some not, and non-compliant as none of it met.

1. Each link adds facts about the target, from its relationship and its source's result:

   | Relationship | Source compliant | Source partially compliant | Source non-compliant |
   |---|---|---|---|
   | `equal` | all met | some met, some unmet | all unmet |
   | `superset` | all met | — | all unmet |
   | `subset` | some met | some met, some unmet | some unmet |
   | `intersect` | some met | — | some unmet |

   A `not_assessed` source adds nothing, nor does a `not_applicable` source on a `subset` or `intersect` link.

2. The facts contradict each other when "all met" comes with an unmet fact, or "all unmet" with a met fact. The target's facts then come from its `equal` and `superset` links only; if those still contradict each other, the target takes the most restrictive of their results.

3. The target's result is the first that applies: all met, compliant; some met, partially compliant; some or all unmet, non-compliant; a `not_applicable` source on an `equal` or `superset` link, not applicable; otherwise `not_assessed`.

A multi-hop path applies the rule hop by hop, each hop reading the results the previous one inferred.

## Consequences

- With consistent inputs, the inferred compliance never overstates the target's: it is exact when the facts settle it, and otherwise the lowest value they allow. A single partial link gives what it gave before: a compliant `subset` or `intersect` source makes the target partially compliant.
- Results change where the most restrictive result misread the evidence:

  | Links to one target | Before | Now |
  |---|---|---|
  | `subset` compliant + `subset` non-compliant | non-compliant | partially compliant |
  | `intersect` compliant + `intersect` non-compliant | non-compliant | partially compliant |
  | `equal` partially compliant + `subset` non-compliant | non-compliant | partially compliant |
  | `equal` compliant + `subset` or `intersect` not assessed | not assessed | compliant |
  | `superset` or `intersect` partially compliant, alone | partially compliant | not assessed |
  | `equal` compliant + `subset` partially compliant (contradiction) | partially compliant | compliant |

- A contradiction is settled in favour of the `equal` and `superset` links, with no mark on the result: A.8.32 above is inferred compliant, and the partially compliant subset shows only among its sources.
- The facts form a set, so the order of the links never changes the result.
- A hop's results never overstate, and a lower result only proves less met or more unmet, so a multi-hop result never overstates either. Each hop loses precision, and a pessimistic intermediate result can create a contradiction the original inputs did not have; it is settled like any other.
- The other mapped fields follow the links' coverage too, independently of their order. Status and observation come from the `equal` and `superset` links. Scores come from those whose scores are comparable, or else from the partial links whose scores are. When several links qualify, one supplies each group of fields: the link with the most restrictive result, then the lowest score, then the first source requirement. The coverage label (weakest link) and the merge strategy of *Map from an audit* stay as they are. `mapping_inference.result` always equals the inferred compliance.
- API clients see the change in the cases above, in `GET /api/compliance-assessments/{id}/frameworks/`, `map_from_preview` and `map_from`, and in the results pre-filled when `POST /api/compliance-assessments/` names a baseline from another framework; the `mapping` management command follows. Stored assessments change only when mapped again. No schema change.
- The reading of the three results is part of the engine's contract. If non-compliant comes to mean "the essential part is not met" while some parts are, "some met, some unmet" no longer proves partially compliant: the rule must change, and `equal` and `subset` partially compliant sources need a fact of their own.
- Every row of both tables keeps a test in `backend/app_tests/api/test_mapping_engine.py`.

## Security considerations

- Nothing new to attack: the rule is a function over source assessments the caller can already read, behind the same endpoints and permissions, and its cost stays linear in the number of links.
- The risk is integrity: an inferred compliance that misstates the target's. The rule lowers it. With consistent inputs it never overstates compliance, which the most restrictive result did through partially compliant `superset` and `intersect` sources.
- We accept that on contradictory inputs the `equal` and `superset` links win, so a target can be inferred compliant while a partial source reports a gap. Inferred results are suggestions an auditor reviews, and the inference panel lists every source with a link to it. To reduce the risk, the inference record should keep each source's own result and the panel should show it, so disagreements are visible; today it shows only the inferred result.
