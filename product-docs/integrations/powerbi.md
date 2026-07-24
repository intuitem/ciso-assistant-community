---
description: >-
  Build your own Power BI reports on top of CISO Assistant: install the native
  connector, load ready-to-model tables scoped to your permissions, and create
  drillable dashboards without writing any API code.
---

# Power BI connector

Compatible with: SaaS or on-premises, CE or Pro. Requires Power BI Desktop (Windows).

The connector adds **CISO Assistant** to Power BI's *Get Data* dialog. It handles the technical plumbing for you — API pagination, authentication, data typing, incremental refresh — and serves your data as flat, ready-to-relate tables. Access control is preserved end to end: the connector authenticates with **your** Personal Access Token, so reports only ever contain the domains and objects your account can see in the application.

### Install the connector

Both files are attached to each connector release on GitHub. Pick one path:

| | Path A — signed `.pqx` (recommended) | Path B — `.mez` |
| --- | --- | --- |
| Power BI security level | Keeps the default **(Recommended)** setting | Must be lowered to *allow any extension* |
| Workstation privileges | Admin needed once (trust our certificate) | None |
| Best for | Managed workstations, gateway servers | Quick evaluation |

**Both paths**: copy the file into `Documents\Power BI Desktop\Custom Connectors` — and keep only one of the two files there.

{% hint style="warning" %}
On OneDrive-connected machines, "Documents" is often `...\OneDrive\Documents`, not `C:\Users\<you>\Documents`. A connector placed in the wrong folder is silently ignored. This PowerShell snippet always resolves the right one:

```powershell
$dir = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Power BI Desktop\Custom Connectors"
New-Item -ItemType Directory -Force $dir | Out-Null
Copy-Item .\CisoAssistant.pqx $dir -Force
```
{% endhint %}

**Path A**: ask IT to add the connector certificate's thumbprint (published with each release) to the trusted list — a single registry value under `HKLM\Software\Policies\Microsoft\Power BI Desktop`, deployable by GPO. Restart Power BI Desktop; the connector loads with security kept at **(Recommended)**.

**Path B**: in Power BI Desktop, set **File → Options and settings → Options → Security → Data Extensions** to *Allow any extension to load without validation or warning*, restart. Note this lowers the bar for every extension on the machine — prefer Path A where possible. Switching to Path A later is seamless: your reports and credentials are untouched.

### Connect

1. Create a Personal Access Token: avatar menu → **My profile** → **Settings** → **Personal Access Tokens** → **Generate new token**. Full walkthrough: [Generating a PAT](pat.md). Copy the token — it is only displayed once.
2. In Power BI Desktop: **Get Data** → search "CISO Assistant" (category *Online Services*) → enter the URL you use in your browser, e.g. `https://ciso-assistant.example.com` (no `/api` suffix).
3. Paste the token when prompted, then pick tables in the Navigator and **Load**.

{% hint style="info" %}
Always use an `https://` URL — the token is sent with every request. The connector refuses plain `http://` except toward local/private development hosts.
{% endhint %}

When the token expires, generate a new one and update it under **File → Options and settings → Data source settings → Edit Permissions**.

### Understand the tables

The Navigator groups tables in three folders. The grouping is the key to building correct reports:

* **Facts** — the things you count and measure: requirement assessments, applied controls, findings, evidences, incidents, risk scenarios, vulnerabilities, security exceptions, assets. When a chart shows a number, it comes from a fact.
* **Dimensions** — what you slice *by*: folders (domains), frameworks, compliance assessments (audits), requirement nodes, risk assessments, perimeters, threats, reference controls, findings assessments, labels.
* **Bridges** — two-column link tables for many-to-many relationships (e.g. *Risk Scenario - Threat*). One row per link; they let Power BI count across relationships correctly.

A useful mental shortcut: *"show me X per Y, considering which X relates to Z"* — X is a fact, Y is a dimension, Z goes through a bridge.

Three things that surprise Power BI newcomers:

* **Relating tables never adds columns.** Loading a bridge does not make a threat column appear on the risk scenario table; instead, relationships let a *visual* combine fields from several tables. To see linked records side by side, put fields from both tables in one visual (see the recipes below).
* **Label columns are slicers too.** Fields like `status`, `severity` or `result` live directly on the fact tables — drag them straight into a legend or slicer. Only rich, shared context (frameworks, folders…) gets its own dimension table.
* **`*_id` columns are join keys.** Relate tables on `id` ↔ `*_id` pairs only (e.g. `Applied Controls[folder_id]` → `Folders[id]`). Same-named text columns like `ref_id` are **not** join keys.

{% hint style="info" %}
Some audit fields (e.g. scores) can be hidden per audit by its field visibility configuration. Hidden fields arrive as empty values in Power BI — the connector mirrors exactly what the application would show your role.
{% endhint %}

### Start from the template

The release also ships `starter.pbit`, a template with a curated set of tables, correct relationships, base measures and four ready-made pages (compliance results, control status, threat coverage, incidents & vulnerabilities). Open it, enter your URL and token, and adapt from there — it is the fastest way to a working report and a reference for how the model is meant to be wired.

### Recipes

All of these are validated patterns you can reproduce in a blank report.

**Control status per domain (drillable bars)** — Stacked bar chart. Y-axis: `folder_name`; X-axis: count of `id` (Applied Controls); Legend: `status`. For a domain hierarchy, use `parent_folder_name` then `name` from the Folders dimension instead (requires the `folder_id` → `Folders[id]` relationship). Use the drill-mode arrows on the visual to descend on click.

**Audit results with a requirement detail table** — Stacked bar chart. Y-axis: `folder_name`, then `compliance_assessment_name` (both are on Requirement Assessments — no relationships needed); X-axis: count of `id`; Legend: `result`. Add a Table visual with `requirement_ref_id`, `requirement_name`, `description`, `result`: clicking any bar segment filters the table to the actual requirements behind it.

{% hint style="warning" %}
Always filter Requirement Assessments on `assessable = True` (a page- or report-level filter works best). Audits also carry rows for non-assessable section headings, which would otherwise inflate every count.
{% endhint %}

**Top threats by scenario coverage (treemap)** — Load `Risk Scenarios`, the `Risk Scenario - Threat` bridge and `Threats`; relate the bridge's two `*_id` columns to each table's `id`. Treemap: Group = `Risk Scenarios[folder_name]` then `Threats[name]`; Values = count of the **bridge's** `risk_scenario_id`. Counting bridge rows is the trick: each row is one scenario↔threat link, so per-threat counts are exact — no formulas needed.

**Explore controls freely (decomposition tree)** — Analyze: count of `id` (Applied Controls); Explain by: `folder_name`, `category`, `status` (add `csf_function`, `priority`, `effort` at will). The viewer picks the split order while exploring — the most self-service-friendly visual in Power BI.

**Cumulative incidents over time** — New quick measure → *Running total*: base value count of `id` (Incidents), field `reported_at`. Line chart with `reported_at` (month level) on the X-axis and the measure on Y. The line only goes up — that's the check it's really cumulative.

**Vulnerability severity funnel** — Power BI's funnel visual draws per-category counts; it computes nothing cumulative by itself. For ordered severities: add a conditional column `severity_rank` in Power Query (Critical→0, High→1, Medium→2, Low→3), select the `severity` column → **Sort by column** → `severity_rank`. For a true "this severity or worse" funnel, add a measure:

```
Vulns This Severity or Worse =
VAR CurrentRank = SELECTEDVALUE(Vulnerabilities[severity_rank])
RETURN CALCULATE(
    COUNTROWS(Vulnerabilities),
    REMOVEFILTERS(Vulnerabilities[severity], Vulnerabilities[severity_rank]),
    Vulnerabilities[severity_rank] <= CurrentRank
)
```

Sort the funnel descending so the widest "everything" stage sits on top.

{% hint style="info" %}
If counts display as "2K" or "0K": select the visual → Format → Data labels → set **Display units** to *None*. Auto units round aggressively at GRC scale.
{% endhint %}

### Incremental refresh

Fact tables support Power BI incremental refresh natively:

1. Define the `RangeStart`/`RangeEnd` parameters (type Date/Time).
2. Filter the fact table on `updated_at` (or `created_at`): *is after or equal to* `RangeStart` and *is before* `RangeEnd`.
3. Configure the incremental refresh policy on the table.

The filter is translated into API query parameters, so scheduled refreshes only transfer the rows that changed in the window instead of the full table.

### Scheduled refresh in the Power BI Service

Custom connectors require an **on-premises data gateway**: place the connector file in the gateway's custom connector folder (Path A's `.pqx` + thumbprint trust applies to gateway hosts too) and enable custom connectors in the gateway settings. See Microsoft's [gateway custom connectors documentation](https://learn.microsoft.com/en-us/power-bi/connect-data/service-gateway-custom-connectors).

### Troubleshooting

* **The connector doesn't appear in Get Data** — the file is in the wrong Documents folder (OneDrive redirection — see Install) or, for `.mez`, the Data Extensions security option still blocks uncertified extensions. The folder name is exactly `Power BI Desktop\Custom Connectors`.
* **Power BI invented relationships between `ref_id` columns** — that's Desktop's relationship *autodetect* matching same-named columns across tables. Turn it off (**File → Options → Current file → Data Load → Autodetect new relationships…**), delete the bogus relationships in Model view, and only ever relate `id` ↔ `*_id`. The starter template ships with autodetect already off.
* **"Can't determine relationships between the fields"** — the visual mixes tables with no relationship path. Either use the denormalized columns of one table (e.g. `folder_name` on the fact itself) or create the missing relationship in Model view.
* **Drill-down fails with a missing-relationship error** — the next drill level's table has no *active* relationship. With autodetect off, every relationship is manual: check it exists and the line is solid (dashed = inactive). Keep cross-filter direction *Single* unless a slicer genuinely needs *Both* — every *Both* edge is a potential ambiguity loop.
* **"CISO Assistant rejected your Personal Access Token"** — the token expired or was revoked. Generate a new one and update it in *Data source settings*.
* **Score columns are empty although the audit has scores** — the audit's field visibility hides them for your role; this is by design (see the hint above).
* **Values like `compliant` / `in_progress` instead of pretty labels** — some columns carry raw values. Rename them in Power Query (*Replace Values*) if you want display labels in legends.
