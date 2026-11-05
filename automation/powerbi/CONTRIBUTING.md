# Developing the Power BI connector

## Layout

```text
automation/powerbi/
├── DESIGN.md            # architecture decisions — read first
├── README.md            # user-facing install/usage doc
├── contract.json        # data contract shared by the connector and backend tests
├── audit_navigator.py   # CI guard: navigator entries may only be appended
├── connector/           # Power Query SDK project (CisoAssistant.pq + assets)
├── signing/             # certificate generation + customer trust runbooks
└── samples/             # starter .pbit template
```

The backend contract test lives at
`backend/app_tests/api/test_api_powerbi_contract.py` and runs with the
regular backend test suite: it asserts that every JSON path consumed by
`connector/CisoAssistant.pq` (as declared in `contract.json`) is present in
the live serializer output. **When you change columns, update
`CisoAssistant.pq` and `contract.json` together.**

## Environment: Windows required for build/test

The M source (`CisoAssistant.pq`) can be edited anywhere (VS Code +
`PowerQuery.vscode-powerquery` for syntax/IntelliSense on macOS/Linux), but
building and evaluating requires Windows:

- The **Power Query SDK** VS Code extension (`PowerQuery.vscode-powerquery-sdk`)
  is Windows-only (wraps `PQTest.exe` / `MakePQX.exe`; not available for
  Mac Silicon, Rosetta doesn't work).
- **Power BI Desktop** is Windows-only.

On Apple Silicon: Parallels Desktop + Windows 11 ARM (~5 GB RAM is enough),
repo mounted via Parallels shared folders.

## Build & test loop (Windows VM)

1. Open `automation/powerbi/connector/` as the VS Code workspace.
2. Install the **Power Query SDK** extension; run its *Setup workspace*
   task if prompted (regenerates `.vscode/settings.json`).
3. **Set credential** task → auth kind *Key* → paste a PAT from your dev
   instance. Credentials bind to the exact base URL in the query file —
   change the URL and the SDK may prompt again (*Clear ALL credentials*
   resets a confused state).
4. **Point the test query at your dev instance**: the URL is the literal on
   the last line of `CisoAssistant.query.pq`. This is a local, uncommitted
   edit — the repo keeps the neutral `https://localhost:8443` placeholder;
   never commit your instance URL. From a VM, `localhost` is the VM itself:
   target the host instead (Parallels: the Mac is `10.211.55.2`; run
   `ALLOWED_HOSTS=localhost,127.0.0.1,10.211.55.2 python manage.py runserver 0.0.0.0:8000`
   on the host and use `http://10.211.55.2:8000`). Plain `http://` is
   accepted for loopback/private hosts only; the connector rejects it for
   public hosts (PAT travels in a header).
5. *Evaluate current file* task → results appear in the panel. To inspect a
   specific table or debug a filter, replace the last line with a drill
   expression, e.g.
   `CisoAssistant.Contents("...") {[Name = "Facts"]}[Data] {[Name = "Applied Controls"]}[Data]`
   (optionally wrapped in `Table.SelectRows(..., each [updated_at] >= #datetime(...))`
   to watch fold behaviour in the backend logs) — same rule: revert before
   committing.
6. *Build* task (pick **MakePQX**, not MSBuild) → `bin/AnyCPU/Debug/connector.mez`.
   MakePQX names the output after the workspace *folder*; the MSBuild path
   (`CisoAssistant.proj`) names it `CisoAssistant.mez` after the project.
   `.vscode/settings.json` points at the MakePQX name.
7. Copy the `.mez` to the Custom Connectors folder — resolve it via the
   known folder (OneDrive may redirect Documents, especially on fresh VMs).
   Run this from VS Code's integrated terminal, which starts in the workspace
   root; a plain PowerShell window starts in your home directory, where the
   relative source path resolves to nothing:
   ```powershell
   $dir = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Power BI Desktop\Custom Connectors"
   New-Item -ItemType Directory -Force $dir | Out-Null
   Copy-Item bin\AnyCPU\Debug\connector.mez "$dir\CisoAssistant.mez" -Force
   Get-Item "$dir\CisoAssistant.mez" | Select-Object Name, LastWriteTime
   ```
   Check that timestamp. A stale `connector.mez` left in `bin\` by an earlier
   session copies over without complaint, and Desktop then tests the old
   connector while you read the new source.
   Allow uncertified extensions in Power BI Desktop's security options,
   restart Desktop, and test **Get Data → CISO Assistant** end-to-end.
8. Run *TestConnection* task before touching gateway-related code.

### Testing the signed .pqx locally

Pack + sign with the extension's bundled MakePQX (path under
`%USERPROFILE%\.vscode\extensions\...powerquery-sdk...\.nuget\...\tools\`),
then validate through Power BI Desktop, not MakePQX:

1. `MakePQX pack -mz bin\AnyCPU\Debug\connector.mez -t bin\AnyCPU\Debug\CisoAssistant.pqx`
2. `MakePQX sign <pqx> --certificate <pfx> --password <pwd> --replace`
3. Put the `.pqx` in the Custom Connectors folder and **remove the `.mez`**
   there (both present = duplicate connector).
4. Add the signing thumbprint to
   `HKLM:\Software\Policies\Microsoft\Power BI Desktop\TrustedCertificateThumbprints`
   (see `../signing/trust-thumbprint.md`), set Desktop's Data Extensions
   security to **(Recommended)**, restart. Desktop refusing to load the
   connector at Recommended = signature or trust problem; loading = the
   full customer path works.

Known quirk (SdkTools 2.155.2, any host): `MakePQX verify` crashes with a
`System.Threading.Tasks.Extensions` assembly-binding error while printing
its report — the package's `MakePQX.exe.config` lacks binding redirects
for the System.Text.Json dependency chain. CI patches the redirects into
the config before running the tools (see the "Patch MakePQX binding
redirects" step in the workflow); locally, either apply the same patch or
skip `verify` and use the Desktop trust test above, which is the
authoritative check anyway.

`.mez` is just a zip of the connector folder contents — CI
(`.github/workflows/powerbi-connector.yml`) builds it with
`Compress-Archive`, packs it to `.pqx` with `MakePQX`, and signs it when
the signing secrets are configured (see `signing/generate-cert.md`).

## Local backend for testing

Any running CISO Assistant works. For a filter/pagination sanity check
without Power BI:

```bash
curl -H "Authorization: Token $PAT" \
  "https://localhost:8443/api/applied-controls/?limit=2&offset=0&updated_at__gte=2026-01-01T00:00:00Z" -k
```

### Validating pagination changes

The server caps `limit` at `PAGINATE_MAX`, so the connector takes its page
stride from the number of rows a response actually contains. That makes the
page size a *server* variable: run the backend with `PAGINATE_MAX` set low
and the connector must still import every row.

```bash
PAGINATE_MAX=200 python manage.py runserver 0.0.0.0:8000
```

`backend/app_tests/api/test_api_powerbi_contract.py` ports the algorithm to
Python and runs it against a clamped API in CI, which catches the arithmetic.
What only the VM can confirm is that M behaves the same:

- a table with more rows than the ceiling → imported row count equals the
  count shown in CISO Assistant (`PAGINATE_MAX=200`, then again unset)
- an empty table → no error, zero rows
- `samples/starter.pbit` refreshes end to end against the clamped instance

**Watch the backend request log, not just the row counts.** Paging defects
come in two kinds and only one of them is visible in Desktop. Fetching too
*few* rows shows up as a short table. Fetching too *many times* does not show
up at all — the rows are correct, the refresh is just slow — so it has to be
counted at the server. Keep `runserver`'s log in view and check:

- a preview of a table **smaller** than the requested count issues **one**
  request, not one per stride to the end of the count (the regression that
  reached review in 1.1.0: `count = 1000` against a 5-row table fired 200
  requests and returned the right 5 rows)
- a full load of a table of N rows issues about `N / served` requests, where
  `served` is the page size the first response actually returned
- each bridge scan carries `fields=id,<m2m>`; if those are absent the
  narrowing silently fell back to full rows (`GetBridgeRows`' `try`)

## Adding a table or a bridge

Append the navigator entry to the end of its group — never insert or reorder.
Reports built with connector ≤ 1.0.1 navigate by position, so moving an entry
silently repoints their queries at a different table. CI enforces this on every
PR (`automation/powerbi/audit_navigator.py`, run against the PR's base).

Then keep `contract.json` in step with the column spec: the backend contract
test reads it and fails when a path the connector consumes stops existing.
Adding a table means seeding one instance of it in that test's `bi_dataset`
fixture, and a fact declared `foldDates = true` also belongs in the
incremental-refresh test's endpoint list.

## Versioning & release

The connector version is the `[Version = "x.y.z"]` attribute on the first
line of `CisoAssistant.pq` — semver, aligned with the compatibility policy:

- **patch** — fixes, no contract change
- **minor** — additive only (new tables/columns/bridges); never breaks an
  existing report
- **major** — renames/removals in the contract, auth or data source kind
  changes; requires migration notes and should be avoided (`contract.json`
  + the backend contract test exist to keep changes additive)

Release: bump `[Version]` (and `contract.json`/docs if the surface changed),
merge, then tag `powerbi-v<x.y.z>`. CI refuses tags that don't match the
`.pq` version, then builds, packs, signs (if the signing secrets are
present), uploads artifacts, and creates the GitHub Release with
`CisoAssistant.mez` + `CisoAssistant.pqx` attached atomically (releases are
immutable once published — assets cannot be added afterwards).

> **Warning**: deleting a published (immutable) release **permanently
> reserves its tag name** — GitHub blocks re-creating that tag forever
> (learned the hard way with `powerbi-v1.0.0`). A botched release is never
> re-cut under the same version: fix, bump patch, tag the next number. Customer upgrade = replace the
file, restart Power BI (reports and credentials bind to the data source
kind, not the file or version).
