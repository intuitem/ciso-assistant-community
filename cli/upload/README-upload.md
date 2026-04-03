# Upload Folder (Drop-and-Run)

Place your EBIOS JSON files in this folder, then run:

```powershell
cd C:\Users\Godmod\Documents\ciso-assistant-community\cli
C:\Users\Godmod\Documents\ciso-assistant-community\.venv\Scripts\python.exe .\import_ebios_json_package.py --folder "Global" --matrix "4x4 risk matrix from EBIOS-RM"
```

The importer reads this folder by default.

Expected JSON files (arrays):

- assets.json
- risk_sources.json
- threats.json
- risk_events.json
- risk_scenarios.json

Optional JSON files:

- controls.json
- stakeholders.json
- target_objectives.json
- ro_to_pairs.json
- strategic_scenarios.json
- operational_scenarios.json
- risk_register.json
- mitigation_strategies.json (or mitigation_strateghies.json)
- compliance_controls.json
- audits.json

Replay tips:

- Workshop 2/3/4 only:

```powershell
C:\Users\Godmod\Documents\ciso-assistant-community\.venv\Scripts\python.exe .\import_ebios_json_package.py --folder "Global" --matrix "4x4 risk matrix from EBIOS-RM" --extras-only --skip-feared-events
```

- Use `--input-dir` only if your files are in another folder.
