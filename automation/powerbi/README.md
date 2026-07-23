# CISO Assistant Power BI Connector

A Power BI custom connector that exposes your CISO Assistant data as
ready-to-model tables: open Power BI Desktop, **Get Data → CISO Assistant**,
enter your instance URL and a Personal Access Token, and start building
reports.

Everything technical is handled for you:

- **Pagination** — the connector walks the API pages transparently.
- **Star schema** — data arrives as flat fact/dimension tables plus bridge
  tables for many-to-many relationships, ready for Power BI's model view.
- **Permissions** — the connector uses the regular CISO Assistant API with
  your own token, so you only ever see the domains and objects your account
  is allowed to see. There is no service account and no side channel.
- **Incremental refresh** — fact tables translate Power BI's
  `RangeStart`/`RangeEnd` filters on `updated_at`/`created_at` into API-side
  filters, so scheduled refreshes only pull what changed.

## Tables

| Group | Table | Contents |
|---|---|---|
| Facts | Requirement Assessments | One row per audit requirement, with result, score, status |
| Facts | Applied Controls | Controls with status, dates, progress |
| Facts | Findings | Findings with severity, status, deadlines |
| Facts | Evidences | Evidence records with status and links |
| Facts | Incidents | Incidents with severity, detection, timestamps |
| Facts | Risk Scenarios | Risk register rows with current/residual levels (name, value, color) |
| Facts | Vulnerabilities | Vulnerabilities with severity, status, SLA state, key dates |
| Facts | Security Exceptions | Exceptions with severity, status, expiration date |
| Facts | Assets | Asset inventory (type, class, primary flag) |
| Dimensions | Compliance Assessments | Audits (name, framework, perimeter, progress) |
| Dimensions | Frameworks | Loaded frameworks |
| Dimensions | Requirement Nodes | Framework requirements (for drill-down by ref_id) |
| Dimensions | Folders | Domains, for slicing by organisational scope |
| Dimensions | Risk Assessments | Risk assessments (status, matrix, perimeter) |
| Dimensions | Perimeters | Perimeters for audit/risk slicing |
| Dimensions | Threats | Threat catalog entries |
| Dimensions | Reference Controls | Control catalog (category, CSF function) |
| Dimensions | Findings Assessments | Findings campaigns (category, treatment progress) |
| Dimensions | Labels | Your own cross-cutting labels |
| Bridges | 20 link tables | Many-to-many links (e.g. Requirement Assessment ↔ Applied Control, Risk Scenario ↔ Threat, Vulnerability ↔ Asset, fact ↔ Label) |

Datetime columns are normalised to UTC.

## Installation (Power BI Desktop)

Both variants of the connector are attached to each release; pick the
installation path that fits your environment:

| | Path A — signed `.pqx` (recommended) | Path B — `.mez` |
|---|---|---|
| Security level | Keeps Power BI's **(Recommended)** data-extension security | Requires lowering it to *allow any extension* |
| Workstation privileges | **Admin required once** (registry entry to trust our certificate, deployable by GPO) | None |
| Best for | Managed/corporate workstations, gateway servers | Quick evaluation, machines where you can't touch the registry |

Common first step for both — copy the connector file to
`Documents\Power BI Desktop\Custom Connectors` (create the folder if
needed). **Careful**: "Documents" here is the Windows *known folder*,
which on OneDrive-connected accounts is `...\OneDrive\Documents`, not
`C:\Users\<you>\Documents` — a connector placed in the wrong one is
silently ignored. This resolves it reliably:

```powershell
$dir = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Power BI Desktop\Custom Connectors"
New-Item -ItemType Directory -Force $dir | Out-Null
Copy-Item .\CisoAssistant.pqx $dir -Force   # or CisoAssistant.mez for path B
```

Keep only one of the two files in that folder — both at once makes the
connector appear twice.

**Path A (signed `.pqx`)**: have IT add our signing certificate's
thumbprint to the trusted list — one registry value, admin required,
GPO-deployable for fleets; the runbook with the current thumbprint is
[signing/trust-thumbprint.md](signing/trust-thumbprint.md). Power BI
Desktop then loads the connector at the **(Recommended)** security level
after a restart — no security setting is changed.

**Path B (`.mez`)**: in Power BI Desktop, set **File → Options and
settings → Options → Security → Data Extensions** to *Allow any extension
to load without validation or warning*, then restart. Note this setting
lowers the bar for **every** extension on the machine, not just this one —
prefer path A where possible.

Switching from B to A later is seamless: swap the file, add the registry
trust, restore the security level — existing reports and credentials are
untouched (they bind to the connector's identity, not the file).

## Creating a Personal Access Token

1. In CISO Assistant, open **My profile** (avatar menu) → **Settings** →
   **Personal Access Tokens**.
2. Create a token, choose an expiry (days), and copy the value — it is only
   displayed once.
3. In Power BI, when prompted by the connector, paste it as the key.

Note: the token carries exactly your permissions. When it expires, create a
new one and update it under **Data source settings → Edit Permissions** in
Power BI.

## Connecting

1. **Get Data → CISO Assistant** (category *Online Services*).
2. Enter the URL you use in your browser, e.g.
   `https://ciso-assistant.example.com` (no `/api` suffix). Always use an
   `https://` URL for real instances — your token is sent with every
   request; reserve plain `http://` for local development servers.
3. Paste your Personal Access Token when prompted.
4. Pick tables in the Navigator (Facts / Dimensions / Bridges) and **Load**.

## Modeling tips

- Relate facts to dimensions on the `*_id` columns
  (e.g. `Requirement Assessments[compliance_assessment_id]` →
  `Compliance Assessments[id]`).
- Bridge tables carry two id columns; set both relationships to the bridge
  and mark one as bidirectional if you need cross-filtering.
- The starter template in `samples/` ships with these relationships
  pre-wired.

## Incremental refresh

Fact tables support Power BI incremental refresh out of the box:

1. Define the `RangeStart`/`RangeEnd` parameters (type Date/Time).
2. Filter the fact table on `updated_at` (>= RangeStart, < RangeEnd) or
   `created_at`.
3. Configure the incremental refresh policy on the table.

The filter is folded into API query parameters — refreshes only transfer
rows in the window.

## Scheduled refresh (Power BI Service)

Custom connectors require an **on-premises data gateway**: place the
connector file in the gateway's custom connector folder and enable custom
connectors in the gateway settings. See Microsoft's
[gateway custom connectors documentation](https://learn.microsoft.com/en-us/power-bi/connect-data/service-gateway-custom-connectors).

## Troubleshooting

- **Power BI created strange relationships (e.g. between two `ref_id`
  columns)** — that's Desktop's relationship autodetect matching same-named
  columns across tables. Disable it in File → Options → Current file →
  Data Load, delete the wrong relationships in Model view, and relate
  tables on `id` ↔ `*_id` columns only. The starter template ships with
  this already configured.
- **The connector doesn't appear in Get Data** — the `.mez` is in the wrong
  Documents folder (OneDrive redirection, see Installation) or the Data
  Extensions security option still blocks uncertified extensions. The folder
  name is exactly `Power BI Desktop\Custom Connectors` (no "Microsoft").
- **"CISO Assistant rejected your Personal Access Token"** — the token is
  expired or revoked. Create a new one and update the credential.
- **Columns show null that have values in the app** — some audit fields
  (e.g. scores) are hidden per-audit via field visibility; hidden fields
  arrive as null, mirroring what the app shows your role.
- **Refresh pulls everything despite incremental refresh** — ensure the
  range filter is applied directly on the fact table's `updated_at` or
  `created_at` column with `>=` and `<` (the default of the incremental
  refresh dialog).
