# Upload Assets From CSV

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