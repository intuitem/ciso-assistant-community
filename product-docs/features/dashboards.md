---
description: Compose grids of widgets over custom and built-in metrics
---

# Dashboards

**Dashboards** are part of the **Metrology** module. They're how you assemble metrics into views you can share, embed, or revisit over time — KPI cards, charts, gauges, sparklines, tables, or Markdown blocks, arranged on a grid.

A dashboard is useful on its own — open it from **Metrology → Dashboards** and read the widgets directly. Optionally, an instance-wide default dashboard can also be plugged into the **Custom** tab of the [Analytics](analytics.md) page.

## Where dashboards live

In the sidebar, under **Metrology**, alongside **Metric definitions** and **Metric instances**:

- **Metric definitions** — the templates (what a metric measures, its unit, how it's computed).
- **Metric instances** — instantiated metrics tied to a domain and updated over time.
- **Dashboards** — visualisations composed over those metrics (and over built-in metrics the platform computes for you).

Dashboards are the visualisation layer of Metrology. They don't carry data themselves — they read it from metric instances and built-in object metrics.

## What a dashboard holds

| | |
|---|---|
| **Name + reference ID** | What it's called. |
| **Domain** | The folder it belongs to; drives IAM scoping. |
| **Layout** | Column count and row height (defaults: 12 columns, 100 px row height). |
| **Global filters** | Default time range + refresh interval that widgets can inherit. |
| **Widgets** | The grid contents — one widget per cell, draggable and resizable. |

## Widgets

Each widget renders exactly one of three data sources, picked when you create the widget:

- **A custom metric** — a **MetricInstance** you authored. Best for org-specific indicators.
- **A built-in metric** — a system-computed value attached to a known object (e.g. `progress` on a `ComplianceAssessment`, `result_breakdown` on an audit). Bind by content type + object ID + metric key. Refreshes itself when the underlying object changes.
- **A text block** — static Markdown for headings, dividers, narrative.

### Chart types

| Type | Use for |
|---|---|
| **KPI Card** | A single headline number |
| **Donut** / **Pie Chart** | Composition (status mix, severity mix) |
| **Bar** / **Line Chart** / **Area Chart** | Trends over time |
| **Gauge** | Progress toward a target |
| **Sparkline** | Inline mini-trend |
| **Table** | Tabular drill-down |
| **Text** | Static Markdown content |

Each widget can also carry a custom title, an **aggregation** (avg, sum, min, max, count, last value), and a **time range** (last hour / 24 hours / 7 days / 30 days / 90 days / year / all-time / custom).

## Authoring a dashboard

1. Open **Metrology → Dashboards** and click **Create a dashboard**.
2. Set the name, domain, optional ref ID, optional labels.
3. From the new dashboard's detail page, open the **Widgets** layout view.
4. **Add a widget** — pick a chart type, then bind a data source (custom metric, built-in metric, or text block). Give it a title.
5. Drag widgets to reorder, resize for emphasis. Layout changes save in place.

A dashboard with no widgets shows _"No widgets configured for this dashboard yet."_ on every viewing surface, with a shortcut back to the layout editor.

## Embedding a dashboard on the Analytics page

The **Analytics** page exposes a **Custom** tab that embeds one dashboard inline — useful when you want a non-default summary view to appear on the platform's main analytics surface.

How it's wired:

- A single **per-instance default** is stored in global settings as `default_custom_analytics_dashboard`. Every viewer of the Custom tab sees the same dashboard.
- Only users with the `change_globalsettings` permission see the picker; everyone else sees the locked dashboard name and the rendered widgets.
- The picker (admins only) is a searchable popover on top of the dashboard name; pick a dashboard, or **Clear default** to leave the tab empty.

{% hint style="info" %}
The default is **global**, not per-user. If a viewer doesn't have access to the chosen dashboard's domain, they'll see the empty state — not someone else's data. Pick a dashboard whose domain is reachable by your audience.
{% endhint %}

### Empty states on the Custom tab

- **No dashboards exist yet** → _"No dashboards available — Build your first dashboard to use it as a custom analytics tab."_ + a link to create one.
- **Default set, but viewer can't reach it** → empty state, silently.
- **Default set, but the dashboard has no widgets** → _"No widgets configured for this dashboard yet."_ + a shortcut to its **Widgets** editor.

## Built-in vs custom metrics

| Source | When to use |
|---|---|
| **Custom metric** | Your own indicators — `MetricInstance` objects you defined. Update values manually or via the API; chart their evolution. |
| **Built-in metric** | Numbers the platform already computes for known objects — audit progress, compliance result breakdowns, risk-treatment distribution. Bind by content type + object ID + metric key. |

Built-in metrics refresh automatically as the underlying objects change. Custom metrics depend on you keeping their values up to date.

## What's next

- [Metrics](../concepts/metrics.md) — the underlying metric-definition / metric-instance model.
- [Analytics](analytics.md) — the standard Governance / Risk / Compliance tabs that sit alongside the **Custom** tab.
- [My assignments](my-assignments.md) — the sibling personal-dashboard surface for "what's on my plate".
