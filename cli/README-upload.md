# Upload Assets From CSV And Replay JSON Bundle

## Recommended Method: Multi-File EBIOS Package Import

Use this method when your data is split across several JSON files in one folder (for example on `E:/`).

### Step 1 - Go to CLI folder

```powershell
cd C:\Users\Godmod\Documents\ciso-assistant-community\cli
```

### Step 2 - Install dependencies in your venv

```powershell
C:\Users\Godmod\Documents\ciso-assistant-community\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Step 3 - Run the package importer

```powershell
C:\Users\Godmod\Documents\ciso-assistant-community\.venv\Scripts\python.exe .\import_ebios_json_package.py `
	--input-dir E:/ `
	--folder "Global" `
	--matrix "4x4 risk matrix from EBIOS-RM"
```

### What is imported

- Core data via Data Wizard: assets, threats, controls, risk scenarios
- EBIOS RM: study, feared events, RO/TO, stakeholders, strategic scenarios, attack paths, operational scenarios

### Replay modes

- `--extras-only`: re-import workshop 2/3/4 objects only
- `--skip-extras`: import core objects only
- `--skip-feared-events`: keep feared events untouched

Example (workshop 2/3/4 replay only):

```powershell
C:\Users\Godmod\Documents\ciso-assistant-community\.venv\Scripts\python.exe .\import_ebios_json_package.py `
	--input-dir E:/ `
	--folder "Global" `
	--matrix "4x4 risk matrix from EBIOS-RM" `
	--extras-only --skip-feared-events
```

### Troubleshooting

- If terminology errors appear for `ro_to.risk_origin` or `entity.relationship`, rerun with the same command: the importer now creates visible fallback terms as needed.
- If feared events already exist and conflict, rerun with `--skip-feared-events`.
- Ensure `.clica.env` is present and valid (`TOKEN`, `API_URL`, `VERIFY_CERTIFICATE`).

### Known Limitations And Replay Policy

- Scope of this importer: workshop 1 to 4 objects only (core assets/threats/controls/risk scenarios + EBIOS study, feared events, RO/TO, stakeholders, strategic and operational scenarios).
- Terminology behavior: if required visible terms are missing for `ro_to.risk_origin` or `entity.relationship`, importer-specific visible terms can be created to unblock the run.
- Rerun safety: preferred rerun mode after a first successful load is `--extras-only --skip-feared-events` to avoid duplicate conflicts on feared events.
- Idempotency model: most objects are upserted (update-or-create) using references or stable keys; however, malformed or duplicated source refs can still produce conflicts.
- Input contract: JSON files are expected as arrays and must keep stable `ref_id` values across reruns.
- Recommended production sequence:
	1. Initial load with full command.
	2. Iterative workshop updates with `--extras-only --skip-feared-events`.
	3. Full replay only when source package structure has changed significantly.

## Replay A Full JSON Bundle

If your source of truth is a single JSON bundle instead of a CSV, use the dedicated orchestrator from the `cli/` folder.

```powershell
cd C:\Users\Godmod\Documents\ciso-assistant-community\cli
C:\Users\Godmod\AppData\Local\Programs\Python\Python312\python.exe -m pip install -r requirements.txt
C:\Users\Godmod\AppData\Local\Programs\Python\Python312\python.exe .\import_complete_json_bundle.py --input "E:\asset threat scenario control.txt"
```

This single command chain will:

- normalize the JSON into `risk_bundle_fixed.json`
- import `risk_sources`
- import EBIOS RM `feared_events`
- generate the intermediate CSV files
- import assets, threats, controls, and risk assessment scenarios

If `risk_bundle_fixed.json` already exists in `cli/`, you can simply rerun:

```powershell
C:\Users\Godmod\AppData\Local\Programs\Python\Python312\python.exe .\import_complete_json_bundle.py
```

---

This guide explains how to import many assets into CISO Assistant from a CSV file using the CLI.

## Prerequisites

The following files are already in place:

- `.clica.env`
- `requirements.txt`

If Python is not yet on your `PATH`, use the full executable path below.

## Step 1 - Go to the CLI folder

```powershell
cd C:\Users\Godmod\Documents\ciso-assistant-community\cli
```

## Step 2 - Install dependencies

```powershell
C:\Users\Godmod\AppData\Local\Programs\Python\Python312\python.exe -m pip install -r requirements.txt
```

## Step 3 - Check the list of available folders

This lets you confirm the exact folder name to use with `--folder`.

```powershell
C:\Users\Godmod\AppData\Local\Programs\Python\Python312\python.exe clica.py get-folders
```

## Step 4 - Prepare the CSV file

Minimal example:

```csv
name,description,domain,type
asset1,relevant information,Global,PR
asset2,relevant information,Global,SP
```

Supported columns for `import-assets`:

- `name` required
- `ref_id`
- `description`
- `type` with values `PR`, `SP`, `primary`, or `support`
- `domain`
- `business_value`
- `localisation` or `location`
- `observation`
- `reference_link` or `link`
- `security_objectives` or `security_capabilities`
- `disaster_recovery_objectives` or `recovery_capabilities`
- `parent_assets`
- `labels`, `filtering_labels`, `étiquette`, or `label`

## Step 5 - Run the import

Exact command for a CSV file named `assets.csv` in the `cli` folder:

```powershell
C:\Users\Godmod\AppData\Local\Programs\Python\Python312\python.exe clica.py import-assets --file .\assets.csv --folder "Global"
```

If you want existing records to be updated instead of stopping on conflicts:

```powershell
C:\Users\Godmod\AppData\Local\Programs\Python\Python312\python.exe clica.py import-assets --file .\assets.csv --folder "Global" --on-conflict update
```

Ready-to-use helper script (generic):

```powershell
.\import-assets.ps1
```

Examples:

```powershell
.\import-assets.ps1 -File .\assets.csv -Folder "Global"
.\import-assets.ps1 -File .\assets.csv -Folder "Global" -OnConflict update
```

## One-Click Import For Your Own File

For maximum simplicity, use the dedicated script:

1. Prepare your CSV file named `mes_assets.csv` in the `cli/` folder
2. Run:

```powershell
cd C:\Users\Godmod\Documents\ciso-assistant-community\cli
.\import-mes-assets.ps1
```

That's it. No parameters, no complications. The script imports from `mes_assets.csv` directly.

## Example With The Sample File

```powershell
C:\Users\Godmod\AppData\Local\Programs\Python\Python312\python.exe clica.py import-assets --file .\sample_assets.csv --folder "Global"
```

## `localisation` Column

The asset importer accepts:

- `localisation`
- `location`

Both are mapped to the Asset `localisation` field during import.