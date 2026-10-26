# Data import samples

Messy, realistic files for trying `/experimental/data-import`. `test_mapping_samples.py`
pins what detection makes of each one, so editing a file means updating that test.
Regenerate them with `python make_samples.py <this folder>`.

| File | What it exercises | What detection does today |
|---|---|---|
| `01_cartographie_SI_FR.xlsx` | French headers, a 2-line title banner, two asset tabs, a lookup tab, a readme tab, an unknown domain (`DSI Lyon`) | Both asset tabs → Asset, `Réf.` / `Nom` / `Type` / `Domaine` mapped, `Primaire`/`Support` matched. Lookup and readme tabs left out |
| `02_isms_controls_tracker_EN.xlsx` | Header on row 2 under a note, free-form values (`Done`, `Planned`, `P1`, `Large`), a `Q1 2027` date | → Applied controls, 10 of 11 columns mapped. `Due date` lands on expiry date (you may want ETA); some status and priority words to match |
| `03_vendor_register.xlsx` | Four tabs feeding one third-party import, linked by vendor ID; countries as names | Suppliers, Contracts, Contacts → the right third-party sheets, countries matched. `Services` is not detected: set it to TPRM › Solutions. Map the `Vendor ID` columns to `provider_entity_ref_id` |
| `04_risk_register_FY2026.xlsx` | Risk levels as words, threats and assets as lists | → Risk assessment. `Likelihood`/`Impact` are not matched; `Affected assets` is left for you (linked records need an exact column name). Needs a risk matrix |
| `05_pentest_findings_Q3.csv` | Semicolon CSV, severities and statuses as words | → Findings (from the file name). `Affected asset` left for you; some status words to match |
| `06_journal_incidents_FR.csv` | French CSV: `Gravité`, `Statut`, `Détection` | → Incident. French severity and status words have no backend translation: match them by hand |
| `07_new_joiners.csv` | Users, one row with no names | → User, email mapped. `Given name` / `Surname` to map by hand |
| `08_cmdb_assets_noisy.xlsx` | Asset list drowned in side columns named like other objects' fields (`Status`, `Impact`, `Link`, `Label`, `Owner`), a duplicated `Name` header | → Asset; only `Asset tag`, `Name`, `Description`, `Class` mapped, the side columns left alone. `Class` holds sensitivity levels, not asset classes: the dry run flags it |
| `09_iso27001_internal_audit.xlsx` | Internal audit against ISO 27001:2022 Annex A in the auditor's words; existing measures to create as applied controls; one bad reference `A.99.9` | → Audit. Pick ISO 27001:2022 and a name; map `Auditor notes` → observations and `Existing measures` → applied controls by hand |
| `10_vendor_due_diligence.xlsx` | Third party + its assessment + questionnaire answers, chained: the answers become the audit the assessment links to by `Audit name` | → Entities, EntityAssessments, Audit. Give the audit the same name as the `Audit name` cell; map `Vendor ID` → `entity_ref_id` on the assessment |
| `11_kpi_monthly_pack.xlsx` | KPIs (metric instances of library definitions VULN-01, GOV-02) and monthly values, numeric and maturity levels by name; one misspelt level, one unknown KPI | → Metric instances + samples. Map `Metric` → metric definition and `KPI code` → ref_id / metric instance by hand |
| `12_security_calendar.xlsx` | ISMS calendar under a title banner: recurring activities with a frequency and an "every N" column, owners by email or team, the control each one maintains; one row has a frequency but no interval | → Task templates. Map `Recurring`, `Every` and `Control maintained` by hand; `Owner` goes to assignees. Occurrence history is not mapped |
