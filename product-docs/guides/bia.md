---
description: Step-by-step walkthrough for conducting a Business Impact Analysis
---

# Conducting a Business Impact Analysis

A **Business Impact Analysis** (BIA) measures how badly the organisation hurts when an asset stops working — and how quickly that hurt escalates. Where a risk assessment asks _"what could go wrong?"_, a BIA asks _"if it does, how bad is it after one hour, after one day, after one week?"_.

See [Business impact analyses](../concepts/business-impact-analyses.md) for the underlying object model.

{% hint style="info" %}
BIAs live under **Assets management → Business Impact Analysis** in the sidebar. They're gated by the `bia` feature flag — see [Feature flags](../configuration/settings/feature-flags.md).
{% endhint %}

## Prerequisites

- The `bia` feature flag is on.
- A **perimeter** representing the scope you're analysing (a service, a process, a department). Create one via [Perimeters](../concepts/perimeters.md) if needed.
- **Assets** in scope. Assets must already exist in the inventory — the BIA flow doesn't create them. See [Assets](../concepts/assets.md).
- A **risk matrix** with an impact scale you want to reuse for severity levels. Any enabled matrix from your library will do.

## Big picture: the BIA object graph

A BIA is a thin envelope with three nested layers — each one becomes a separate row in the timeline:

```
Business Impact Analysis
└── Asset assessment (one per asset in scope)
    └── Escalation threshold (one per "step in time")
```

| Object | What it captures |
|---|---|
| **BIA** | Perimeter, risk matrix, due date, authors, reviewers, lock status. |
| **Asset assessment** | One asset in the BIA: its dependencies, the controls protecting it, the evidences, the recovery readiness checklist (`documented` / `tested` / `targets met`). |
| **Escalation threshold** | "At T+_n_ minutes/hours/days, the impact becomes _X_." Several per asset to build the time curve. |

## Step 1 — Create the BIA

1. From the sidebar, open **Assets management → Business Impact Analysis**.
2. Click **Start a BIA**.
3. Fill in the form:
   - **Folder** — the domain this BIA belongs to. Drives IAM scoping.
   - **Perimeter** — the scope of the analysis. Selecting a perimeter auto-fills the folder if it was empty.
   - **Version** — e.g. `0.1` (default), `1.0` once formally approved.
   - **Status** — initial assessment status (Draft, In progress, etc.).
   - **Risk matrix** — the matrix that supplies the impact scale used by escalation thresholds.

     {% hint style="warning" %}
     Changing the risk matrix _after_ thresholds exist auto-clamps each threshold's `quali_impact` to the new scale (between `min_impact` and `max_impact`). The values won't be lost, but **you should review them** — a 4 on a 5-step scale isn't the same severity as a 4 on a 10-step scale.
     {% endhint %}

   - **Due date** — when this must be completed.
   - **Authors** — actors writing the BIA.
   - **Reviewers** — actors expected to review/approve.
4. _Optional_: expand the **More** dropdown to set:
   - **Locked** — when on, no one can edit this BIA or its asset assessments. Use after sign-off to freeze the dossier.
5. **Save**.

## Step 2 — Include assets in the BIA

The BIA detail page opens with the standard `DetailView` plus a **Recovery insights** sidebar widget (it'll show 0% until you populate things) and an **Asset assessments** table below.

For each asset you want in scope:

1. Click **Include asset** (the create button on the asset-assessments table).
2. Fill in:
   - **Asset** — pick the asset; one BIA can't have the same asset twice (`unique_together = ["bia", "asset"]`).
   - **Extra dependencies** — additional assets whose disruption would propagate here. The primary/supporting relationships already declared on the asset are picked up automatically; only add dependencies that aren't already modelled.
   - **BIA** — pre-filled and hidden when adding from the BIA's table.
   - **Associated controls** — controls specifically designed to improve _this_ asset's resilience (e.g. backup job, failover, runbook). These are separate from controls already attached to the asset elsewhere.
   - **Recovery documented** — checkbox. Is there a written recovery procedure?
   - **Recovery tested** — checkbox. Has it been exercised recently?
   - **Recovery targets met** — checkbox. Did the test hit RTO/RPO?
   - **Evidences** — backup tests, DR exercise reports, BCP excerpts.
   - **Observation** — Markdown notes.
3. **Save**.

Each asset assessment surfaces as a row in the BIA's timeline.

{% hint style="info" %}
The three recovery checkboxes drive the **Recovery insights** activity tracker on the BIA header. Each one shows a percentage across all assets in the BIA — your dashboard of "how ready are we" at a glance.
{% endhint %}

## Step 3 — Add escalation thresholds (the time curve)

For each asset assessment, capture how the impact evolves over time. Open the asset assessment's detail page and add thresholds via **Add a step**:

1. **Point in time** — a duration since the start of the disruption. Use the duration picker (days / hours / minutes). Stored internally in seconds. Each `(asset_assessment, point_in_time)` pair must be unique.
2. **Asset assessment** — pre-filled and hidden when adding from inside an asset assessment.
3. **Qualifications** — multi-select from the `qualifications` [terminology](../concepts/terminology.md) (e.g. _financial_, _operational_, _regulatory_, _reputational_). Tags what _kind_ of impact this threshold describes.
4. **Impact** — qualitative impact level, picked from the BIA's risk matrix impact column.
5. **Justification** — free-text rationale.

Build up several thresholds per asset to draw a step curve: _at T+15min: low; T+1h: medium; T+4h: high; T+24h: critical_.

A threshold's impact is **carried forward** until the next threshold — between two threshold points, the curve plateaus at the most recent severity. Before the first threshold, the asset is rendered as `--` (not rated).

## Step 4 — Read the timeline (Impact over time)

From the BIA detail page, click **Impact over time** in the actions column. The page renders the **TimelineTable**:

- Rows: each asset assessment in the BIA.
- Columns: each unique `point_in_time` across the whole BIA (so all rows share an x-axis).
- Cells: the impact severity at that point, colour-coded by the risk matrix.

This is the key output you'll show to stakeholders — at a glance, "if X breaks, here's how the room turns red as time passes".

## Step 5 — Generate the Report

The **Report** button (in the actions column) produces a printable summary:

- BIA header (name, version, status, reference scale).
- Assets included.
- The Impact-over-time TimelineTable.
- **Recovery insights** activity tracker (documented / tested / objectives met percentages).
- **Asset Assessment Status** table — green/grey check icons per asset on the three recovery flags.
- **Objectives vs Capabilities** comparison — per asset, the security objectives and recovery objectives declared on the asset _vs_ the capabilities reported on it, with an **Alignment** verdict (✓ when all aligned, ✗ if any objective isn't met).

Use the **Export PDF** button to print to PDF.

## Step 6 — Export to Excel

For round-trip editing or sharing with people who live in Excel, the actions column also has an **Export → as Excel** option. Goes through `/business-impact-analysis/{id}/export/xlsx`.

## Step 7 — Lock the BIA after sign-off

Once the BIA has been reviewed and accepted, edit it and switch on the **Locked** checkbox in the **More** dropdown.

Effects:

- The detail page shows a yellow banner: _"Assessment Locked — This assessment is locked."_
- Create / Edit / Delete actions are disabled on the BIA and all its asset assessments and escalation thresholds.
- Unlock the same way (uncheck **Locked**) when you start a new revision.

## Step 8 — Request validation (optional)

If the `validation_flows` feature flag is on, the actions column shows a **Request validation** button (hidden when the BIA is locked). It triggers the standard approval workflow — see [validation flows](../introduction/vocabulary.md#v).

## Best-practice sequence

1. Build the asset inventory first; the BIA reads, it doesn't create.
2. Use the **primary/supporting** relationships on assets to model upstream dependencies — the BIA will pick them up for free. Reserve **Extra dependencies** on the asset assessment for things not modelled elsewhere.
3. Pick a risk matrix early and **don't switch matrices** mid-flow unless you're prepared to re-score every threshold.
4. Capture thresholds at organisationally meaningful steps (e.g. SLA breakpoints, regulatory notification windows) rather than evenly spaced.
5. Keep **Authors** small (people who write) and **Reviewers** wider (people who sign off). Lock after the reviewers approve.

## What's next

- Feed the timeline into your [risk assessments](../concepts/risk-assessments.md) — the same asset criticality should drive scenario prioritisation.
- For DORA-regulated entities, the BIA output supports DORA incident-reporting workflows. See [framework-specific features → DORA](../features/framework-specific/dora.md).
- Track the recovery readiness numbers on the **Recovery insights** widget over time as you close gaps.
