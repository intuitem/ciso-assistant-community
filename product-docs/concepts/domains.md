# Domains

> _Draft — placeholder._

A **domain** is a top-level container in CISO Assistant. It represents an organisational scope — a business unit, a subsidiary, a project, or any boundary you want to manage access and reporting around. Sub-domains nest underneath to refine the structure.

## What this page should cover

- The mental model: domain = scope of work + scope of permission.
- Inheritance: how permissions and content cascade from parent to child.
- How a domain relates to perimeters, audits, risk assessments, applied controls.
- Common patterns: one domain per business unit; one domain per customer (in TPRM contexts); a shared "global" domain for cross-org content.

## For users

> _Draft._ How to create, rename, nest, and delete domains. Permission model in plain language. When to use sub-domains vs separate top-level domains.

## For implementers

> _Draft._ A domain is internally a `Folder` (see `backend/core/models.py`). Content-type filtering, the `parent_folder` relationship, IAM scoping rules, the `folder` ForeignKey pattern that almost every business object follows.

## Related

- [Perimeters](perimeters.md)
- [Philosophy → Domains as the unit of scoping](../philosophy.md)
