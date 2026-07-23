# Developing the Power BI connector

## Layout

```
automation/powerbi/
├── DESIGN.md            # architecture decisions — read first
├── README.md            # user-facing install/usage doc
├── contract.json        # data contract shared by the connector and backend tests
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
   instance.
4. Edit `CisoAssistant.query.pq` to point at your dev instance URL
   (`https://localhost:8443` when running the docker compose stack).
5. *Evaluate current file* task → results appear in the panel.
6. *Build* task → `bin/AnyCPU/Debug/CisoAssistant.mez`.
7. Copy the `.mez` to the Custom Connectors folder — resolve it via the
   known folder (OneDrive may redirect Documents, especially on fresh VMs):
   ```powershell
   $dir = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Power BI Desktop\Custom Connectors"
   New-Item -ItemType Directory -Force $dir | Out-Null
   Copy-Item bin\AnyCPU\Debug\connector.mez "$dir\CisoAssistant.mez" -Force
   ```
   Allow uncertified extensions in Power BI Desktop's security options,
   restart Desktop, and test **Get Data → CISO Assistant** end-to-end.
8. Run *TestConnection* task before touching gateway-related code.

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

## Release

Tag `powerbi-v*` → CI builds, packs, signs (if secrets present) and uploads
`CisoAssistant.mez` + `CisoAssistant.pqx` artifacts.
