---
description: How the Community and PRO editions differ, how contributor seats are counted, and where each edition can run
---

# Community vs PRO

CISO Assistant ships in two editions:

- **Community** — the open-source edition, free to use, with the platform's core GRC capabilities. Self-hosted only.
- **PRO** — the commercial edition, built on top of Community, adding enterprise features (sub-domains, focus mode, advanced insights, custom roles, validation flows, and more) plus official support.

A full feature-by-feature comparison lives on the [Community vs PRO page on the intuitem website](https://intuitem.com/compare) — we keep the matrix there so it stays in sync with pricing and release cycles. This page is here to explain the **commercial concepts** that intersect with the platform itself: contributor seats and where PRO runs.

## Contributor seats

PRO is licensed by **contributor seats** — the number of users in your instance who can actually _make changes_.

A user counts as a contributor as soon as they have **any** create / edit / delete permission anywhere in the platform — that is, any role that grants `add_…`, `change_…`, or `delete_…` rights. Concretely, the typical contributor is someone with the **Analyst**, **Domain Manager**, or **Administrator** role (or a custom role that confers similar write rights). Read-only users — anyone whose role only grants `view_…` permissions — do **not** consume a seat.

### Exceptions — who doesn't count

Two narrow categories of users are explicitly **excluded** from the seat count, even though they may perform meaningful work in the platform:

- **Pure approvers** — a user whose _only_ write capability is signing off on a [validation flow](../concepts/validation-flows.md). In practice this is the built-in **Approver** role: its single write permission, `change_validationflow`, is registered as a non-seat permission. If the same user also holds any other write right (e.g. they're an Analyst who happens to be an approver too), the seat is still counted — being an approver doesn't subtract from the count, it just doesn't add one on its own.
- **External third-party representatives** — vendor-side users who log into the [third-party auditee surface](../concepts/third-party-risk.md) to fill in entity assessments. They are flagged as external (`is_third_party`) and are systematically excluded from the count regardless of which write permissions their role grants.

{% hint style="warning" %}
**Internal users helping fill in an audit _do_ consume a seat.** This includes anyone in your own organisation who is assigned to answer requirements via the [Assignment/Respondent mode](../features/assignments.md) feature — most typically users carrying the built-in **Respondent** role, but also any internal teammate whose role grants write access to requirement assessments and evidences. The third-party exception above applies _only_ to vendor representatives reaching the platform through the external auditee surface.
{% endhint %}

The intent behind the two exceptions is narrow: the seat count tracks **internal contributors authoring and maintaining your GRC content**, while sparing two patterns where counting would feel punitive — pure sign-off workflows, and external vendors who don't belong to your organisation in the first place.

### How the count is enforced

The instance compares the number of contributors against the seat allowance carried by your license. The current count is visible from **About CISO Assistant**, opened via the three-dot menu next to your name in the sidebar footer — so you can see at any time how many seats are used and how many are available.

## Where PRO runs

PRO is **available on both deployment models**, and the feature set is identical between them:

- **On-premises** — you host the platform on your own infrastructure (Linux VM, Kubernetes via the [Helm chart](../installation/helm-chart.md), or any of the deployment methods documented under [Installation](../installation/README.md)). Your data stays in your network. This is the right model when sovereignty, air-gapping, or strict residency requirements rule out a managed service.
- **SaaS** — intuitem hosts and operates a managed instance for you. No infrastructure to run, automatic upgrades, backups handled. The right model when you'd rather focus on the GRC programme than on running a Django application.

You can move between the two models — there's no architectural difference, and the data formats (domain exports, library YAML, audit exports) are stable across deployments.

### Unlimited plans

For organisations that don't want to track individual seats — typically large enterprises, MSSPs, public-sector deployments, or any environment where contributor headcount fluctuates often — both the on-premises and SaaS editions are available with an **unlimited plan**. Under an unlimited plan, the platform doesn't enforce a seat count and you don't need to manage role assignments around license limits.

### SecNumCloud

A **SecNumCloud** version is also available, with dedicated hosting under the highest available cloud-security qualification. It is offered in unlimited mode. See the [pricing page](https://intuitem.com/pricing) for details.

## Related

- [Pricing](https://intuitem.com/pricing) — current plan tiers and what each includes.
- [Community vs PRO](https://intuitem.com/compare) — the full feature comparison.
- [Validation flows](../concepts/validation-flows.md) — the governance object whose approvers don't consume a seat.
- [Third-party risk](../concepts/third-party-risk.md) — the auditee surface used by external representatives, who also don't consume a seat.
