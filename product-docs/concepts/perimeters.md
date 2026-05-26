# Perimeters

A **perimeter** is an _optional_ scope refinement an assessment or risk study can be attached to, inside a domain. Where a domain defines _who_ owns the work and _what_ they can see, a perimeter narrows the assessment to _exactly what is being assessed_ — a product, a system, a process, a contract.

Perimeters are optional everywhere they appear: an assessment without a perimeter is scoped to its domain only. Use them when you need to track several distinct scopes inside the same domain, or to roll up assessments by scope rather than by domain.

## When to use a domain vs a perimeter

The two concepts solve different problems — and the choice matters because it shapes both _who can see what_ and _how reports roll up_.

- **Use a domain (or a sub-domain)** when the boundary needs to enforce **IAM scoping** or anchor **reporting**. Domains are where roles are granted, where permissions stop, and where dashboards aggregate. Pick a domain when different teams must have different levels of access, or when leadership wants to see one number per business unit / subsidiary / regulated entity.
- **Use a perimeter** when the boundary is purely **logical**, inside an already-scoped domain. Perimeters split the work into distinct named scopes — a product, a system, a process, a contract — so you can run separate audits or risk studies against each without spinning up extra IAM machinery. Everyone with access to the domain sees every perimeter inside it; there's no per-perimeter access control.

A useful mental check: _"Do these two scopes need different people seeing them?"_ — if yes, they're domains (or sub-domains). _"Do these two scopes need separate assessments but the same audience?"_ — they're perimeters.

## Related

- [Domains](domains.md)
- [Audits](audits.md)
- [Risk assessments](risk-assessments.md)
