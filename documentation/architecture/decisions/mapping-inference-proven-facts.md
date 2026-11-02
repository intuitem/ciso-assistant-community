# Infer mapped compliance from what each link proves

- Status: Proposed
- Date: 2026-10-29
- Deciders: @eric-intuitem

## Context

The mapping engine infers the compliance (`result`) of a target requirement from source assessments, through the links of a requirement mapping set. A link's relationship compares the source with the target: `equal`, `superset` (the source contains the target), `subset` (the source is part of the target) or `intersect`. Several links can reach one target. The inferred results pre-fill an audit created from a baseline in another framework, feed *Map from an audit* ([audit-mapping](../../audit-mapping.md)), and give the compliance distribution of each framework an audit can be mapped to.

The engine kept the most restrictive result over all links, capping a compliant or partially compliant source on a `subset` or `intersect` link at partially compliant, and some paths depended on the order of the links. The most restrictive result misreads consistent evidence: a target with one compliant and one non-compliant subset is non-compliant although part of it is met; a compliant `equal` link next to a `not_assessed` partial one gives `not_assessed`.

Some inputs contradict themselves. `A.12.1.2 —equal→ A.8.32` compliant with `A.14.2.2 —subset→ A.8.32` partially compliant (ISO 27001:2013 to 2022) says that all of A.8.32 is met and that part of it is not. No rule settles that; a rule only picks which source to believe. Mapping relationships are approximations, so such inputs will occur.

Relationships are approximate in a second way: a link records its author's judgment that two requirements share substance, not a measured relation between sets of obligations. Read as exact set relations, links would make the inference provably cautious only in a model the data does not support, and would lose most of what a multi-hop mapping carries. ISO/IEC 27001:2022 reaches NIST CSF 1.1 only through Adobe CCF v5, by `intersect` links at both hops. On the exact reading, a partially compliant source proves nothing through an `intersect` link, so a fully compliant ISO 27001:2022 audit would map to a blank CSF 1.1 audit.

## Decision

We will infer a target's compliance from the facts its links prove about it, reading compliant as all of the requirement met, partially compliant as some of it met and some not, and non-compliant as none of it met. A link carries its source's state to the part the two requirements share, which we take as representative of the source: the link exists because that part is the substance of both.

1. Each link adds facts about the target, from its relationship and its source's result:

   | Relationship | Source compliant | Source partially compliant | Source non-compliant |
   |---|---|---|---|
   | `equal` | all met | some met, some unmet | all unmet |
   | `superset` | all met | some met, some unmet | all unmet |
   | `subset` | some met | some met, some unmet | some unmet |
   | `intersect` | some met | some met, some unmet | some unmet |

   A `not_assessed` source adds nothing, nor does a `not_applicable` source on a `subset` or `intersect` link.

2. The facts contradict each other when "all met" comes with an unmet fact, or "all unmet" with a met fact. The target then takes the most restrictive of the results its links give alone, so a gap any link reports is never hidden.

3. The target's result is the first that applies: all met, compliant; some met, partially compliant; some or all unmet, non-compliant; a `not_applicable` source on an `equal` or `superset` link, not applicable; otherwise `not_assessed`.

A multi-hop path applies the rule hop by hop, each hop reading the results the previous one inferred.

## Consequences

- Only full coverage can make a target compliant. A `subset` or `intersect` link proves at most that some of the target is met, so a target reached only through partial links is at best partially compliant, a result that still asks for work. Within that bound the result is exact when the facts settle it, and otherwise the lowest value they allow. A single link gives what it gave before.
- Results change where the most restrictive result misread the evidence, or depended on the order of the links. No result goes down: over every set of up to three links to one target, the inferred compliance is at least the old one, or, where the old one depended on the order of the links, at least the lowest of its answers.

  | Links to one target | Before | Now |
  |---|---|---|
  | `subset` compliant + `subset` non-compliant | non-compliant | partially compliant |
  | `intersect` compliant + `intersect` non-compliant | non-compliant | partially compliant |
  | `equal` partially compliant + `subset` non-compliant | non-compliant | partially compliant |
  | `equal` compliant + `subset` or `intersect` not assessed | not assessed | compliant |
  | `equal` not applicable + `subset` compliant | compliant or partially compliant, by link order | partially compliant |

- A contradiction is settled by the most restrictive link, as the most restrictive result settled it: A.8.32 above is inferred partially compliant, and a compliant `superset` link with a non-compliant `intersect` link gives non-compliant.
- The facts form a set, so the order of the links never changes the result.
- A multi-hop result keeps the bound: compliance crosses a hop whole only through `equal` and `superset` links, and a partial hop caps it at partially compliant, which later hops carry on. Each hop loses precision, and a pessimistic intermediate result can create a contradiction the original inputs did not have; it is settled like any other. A fully compliant ISO/IEC 27001:2022 audit maps to NIST CSF 1.1 as partially compliant, as before.
- The other mapped fields follow the links' coverage too, independently of their order. Status and observation come from the `equal` and `superset` links. Scores come from those whose scores are comparable, or else from the partial links whose scores are; on a contradiction, only from comparable links that give the target's result, so the result and the score agree. When several links qualify, one supplies each group of fields: the link with the most restrictive result, then the lowest score, then the first source requirement. The coverage label (weakest link) and the merge strategy of *Map from an audit* stay as they are. `mapping_inference.result` always equals the inferred compliance.
- API clients see the change in the cases above, in `GET /api/compliance-assessments/{id}/frameworks/`, `map_from_preview` and `map_from`, and in the results pre-filled when `POST /api/compliance-assessments/` names a baseline from another framework; the `mapping` management command follows. Stored assessments change only when mapped again. No schema change.
- A target reached only through links that prove nothing is inferred not assessed. Before, `subset` and `intersect` links from not applicable sources left it without a result; the frameworks summary now counts it as not assessed, like a target reached from not assessed sources. *Map from an audit* writes nothing for it, not assessed being the default.
- The reading of the three results is part of the engine's contract. If non-compliant comes to mean "the essential part is not met" while some parts are, "some met, some unmet" no longer proves partially compliant: the rule must change, and partially compliant sources need a fact of their own.
- Every row of both tables keeps a test in `backend/app_tests/api/test_mapping_engine.py`.

## Security considerations

- Nothing new to attack: the rule is a function over source assessments the caller can already read, behind the same endpoints and permissions, and its cost stays linear in the number of links.
- The risk is integrity: an inferred compliance that misstates the target's. Compliant, the result that lets an auditor pass over a requirement, comes only from full coverage, and never when a link reports a gap: partial links give at most partially compliant, which still asks for work, and contradictory inputs take the most restrictive link. Non-compliance crosses every link, and turns into partially compliant only when another link shows a met part without contradicting it.
- We accept one approximation: a partially compliant source on a `superset` or `intersect` link makes the target partially compliant, although its met part may lie outside the target, leaving none of the target met. On contradictory inputs the most restrictive link wins, so a target can be inferred lower than its full-coverage links say; that errs toward review. Inferred results are suggestions an auditor reviews, and the inference panel lists every source with a link to it. To reduce the risk, the inference record should keep each source's own result and the panel should show it, so disagreements are visible; today it shows only the inferred result.
