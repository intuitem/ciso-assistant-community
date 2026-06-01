---
description: Per-audit deep-dive dashboard — controls coverage, evidence coverage, threats addressed, scoring radar, timeline, exceptions
---

# Audit advanced analytics

Each compliance assessment carries an **Advanced Analytics** dashboard — a per-audit deep dive that goes beyond the requirement table. It answers the questions an assessor or reviewer actually has: which sections are weakest, how well are we covered with controls and evidences, what threats does this audit address, has our posture improved since the last revision?

The dashboard is gated by the [`advanced_analytics` feature flag](../configuration/settings/feature-flags.md) (default off).

## Where this sits in the analytical stack

The platform offers three layers of analytical depth on top of the regular tables and dashboards. This page documents the **per-audit** layer:

| Surface | Scope | Edition | Gating |
|---|---|---|---|
| **Audit advanced analytics** (this page) | One audit | Community | `advanced_analytics` flag |
| **[Framework report](framework-report.md)** | One framework, every live audit using it | Community | None (permission-gated) |
| **[Insights](insights.md)** menu | Cross-cutting (impact graph, priority/effort, Gantt timeline) | Enterprise (PRO) | None (permission-gated) |

Pick the layer that matches the question you're asking — _is this audit healthy?_, _is this framework healthy across the whole organisation?_, _where should we focus across our entire estate?_

## Where to find it

1. Open a compliance assessment (`/compliance-assessments/<id>`).
2. Locate the **Insights** section in the side panel.
3. Click **Advanced Analytics** (orange chart-line icon).

The button is hidden when the feature flag is off, or for third-party users.

## What it shows

Eight analytical surfaces stream into the page — each loads independently, so the page paints progressively as data arrives:

| Section | Visualisation | What it answers |
|---|---|---|
| **Compliance by Section** | Normalised stacked bars; optional implementation-score radar; optional documentation-score radar; per-section score table | How does each section of the framework fare — proportion compliant / partial / non-compliant / not-assessed, plus implementation and documentation scores when scoring is enabled |
| **Controls Coverage** | Donut + breakdown | What fraction of assessable requirements have at least one applied control linked, plus the status mix of those controls |
| **Compliance Timeline** | Stacked area + score line | Evolution of pass/fail mix and overall score over time |
| **Comparable Audits** | List | Other audits the platform considers comparable (same framework, similar scope) for benchmarking |
| **Implementation Groups Breakdown** | Bar chart | Progress per implementation group defined by the framework |
| **Mapping Projection** | Card list | Which other frameworks this audit can be projected onto via loaded mappings |
| **Evidence Coverage** | Donut + breakdown | Fraction of requirements with evidence, split by direct / indirect / both; status mix of attached evidences |
| **Threats Overview** | Graph + table | Threats addressed by this audit's applied controls; unique threat count |
| **Exceptions Overview** | Stats + table | Security exceptions currently in effect against this audit's requirements |

## When you'd use it

- **Closing-the-loop review** at the end of an assessment cycle — quick read on where to push next year.
- **Pre-audit dry run** — Controls Coverage and Evidence Coverage are the two surfaces that predict how a real audit will go.
- **Benchmarking** — Comparable Audits surfaces other instances of the same framework to look across.

## Related

- [Audits](../concepts/audits.md)
- [Dashboards](dashboards.md) — composed metric views; can embed builtin audit metrics
- [Applied controls analytics](applied-controls-analytics.md) — same kind of dashboard but for controls
- [Insights](insights.md) — Enterprise cross-cutting views beyond a single audit
- [Feature flags](../configuration/settings/feature-flags.md)
