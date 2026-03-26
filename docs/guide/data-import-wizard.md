---
description: Guidelines on data import format
icon: diagram-previous
---

# Data import wizard

{% hint style="info" %}
## Applicable for: Data import wizard UI (Pro) and CLI (Community or Pro)

Importing existing data from excel sheets is supported on the Pro plan through the UI and CLI, and on Community edition through the dedicated CLI, not a django command. The cli is available on the cli folder with the associated instructions.\
Keep in mind that the CLI needs to reach the API as it wraps its actions around it.\
The mention to the API is regarding the fact that users on both plans can still interact with the API directly in case they have some data prep phase on their end for batch import or equivalent.
{% endhint %}

{% hint style="warning" %}
### Connection Error

![](<../.gitbook/assets/image (86).png>)

If you encounter this error, it could be due to the Excel file being protected by **Information Rights Management (IRM)**.

IRM protection restricts access to the file and prevents it from being read by external tools such as data-wizard.

#### How to fix

To resolve this issue, use an unprotected version of the file:

* Download a copy of the file (**File → Create a Copy → Download a Copy**)
* Or export the file as **CSV**
* Or remove IRM protection using the desktop version of Excel
{% endhint %}

## Overview

The **Data Import Wizard** and the **CLI** both support batch creation and updates of fields. They provide the same capabilities; the only difference lies in how the import is initiated:

* through the user interface for the Data Import Wizard
* through the command line for the CLI

When an object already exists during an import, one of the following conflict-resolution strategies can be applied:

* **Stop the import** (default): the import is aborted as soon as a conflict is detected
* **Skip the row**: the existing field is left unchanged and the import continues
* **Update the row**: the existing field is updated with the imported data

The **Update** strategy enables batch updates of existing fields and is particularly useful for changes that could technically be performed through the graphical interface, but become tedious or error-prone when repeated across many objects. In such cases, downloading the existing objects, applying the required transformations in an Excel file, and re-importing the updated data can be significantly faster and more reliable than performing the same actions manually in the UI. This approach reduces repetitive interactions, minimizes the risk of manual mistakes, and provides a clear, auditable workflow for large-scale updates.

In this workflow, it is strongly recommended to retain the **field IDs (UUIDs)** in the import schema. Doing so ensures reliable object matching during re-import, even if other attributes (such as names or labels) have changed, making the update process fail-safe.

If the imported object supports the **domain** attribute, the wizard will attempt to assign it to the specified domain, provided you have the required permissions. If no domain is specified, the wizard will automatically fall back to the default domain configured in the wizard form.



Fields with (\*) are mandatory and don't have any supported fallback.&#x20;

Unless marked as mandatory, ref\_id fields can be left blank but the column must still exist.

&#x20;

## 📦 Assets

### Template

{% file src="../.gitbook/assets/sample001.xlsx" %}

### Supported fields



* ref\_id
* name\*
* description
* domain
* type
  * `PR` : primary
  * `SP` : supporting
*
* reference\_link - URL reference; also accepted as `link`
* observation&#x20;
* filtering\_labels - pipe- or comma-separated label names (created if missing)
* parent\_assets -comma- or pipe-separated list of parent asset `ref_id` values; parent links are resolved after all assets in the file are created, so forward references are supported
* security\_objectives
  * confidentiality: 3,integrity: 2,availability: 1,...
* disaster\_recovery\_objectives
  * rto: 1h01m01s,rpo: 2h01m01s,mtd: 3h
* labels
* is\_business\_function (either true/yes or false/no)

### Special considerations

* type will default to `supporting` if the column does not exist



## ⚙️ Applied controls

### Template

{% file src="../.gitbook/assets/applied_controls_sample (1).xlsx" %}

### Supported fields

* ref\_id
* name\*
* description
* domain
* status
  * `to_do`
  * `in_progress`
  * `on_hold`
  * `active`
  * `deprecated`
* category
  * `policy`
  * `process`
  * `technical`
  * `physical`
  * `procedure`
* priority
  * integer from `1 to 4`
* csf\_function
  * `govern`
  * `identify`
  * `protect`
  * `detect`
  * `respond`
  * `recover`
* effort — size estimate
  * `XS`
  * `S`
  * `M`
  * `L`
  * `XL`
  * full names also accepted, e.g. `Extra Small`
* control\_impact - integer 1–5; also accepted as `impact`
* start\_date - date (YYYY-MM-DD)
* eta - estimated completion date (YYYY-MM-DD)
* expiry\_date - expiry date (YYYY-MM-DD)
* link - URL
* observation - free-text observation
* filtering\_labels - pipe- or comma-separated label names (created if missing)
* reference\_control - lookup by `ref_id`; also accepted as `reference_control_ref_id`
* owner
* amortization\_period - integer (1–50), defaults to 1
* build\_fixed\_cost - number, defaults to 0
* build\_people\_days - number, defaults to 0
* run\_fixed\_cost - number, defaults to 0
* run\_people\_days - number, defaults to 0

### Special considerations

* status will default to `to_do`
* csf\_function will default to `govern`
* The `owner` field resolves against existing users (by email) and teams (by name). Ensure any referenced users and teams are created before importing. Unresolved entries are skipped with a warning and will not block the import.



## 📦 Perimeters

### Template

{% file src="../.gitbook/assets/sample003.xlsx" %}

### Supported fields

* ref\_id
* name\*
* description
* domain
* status
  * `undefined`
  * `in_design`
  * `in_dev`
  * `in_prod`
  * `eol`
  * `dropped`



## 📃 Audits

### Template

{% hint style="info" %}
To avoid any mixup on the expected fields and the requirements reference, you can get a  template for the expected framework by going into `Catalog/Frameworks`
{% endhint %}

The framework needs to be loaded and when clicking on it, you'll see a button to get the excel file.

### Supported fields



* urn\*
* assessable
* ref\_id\*
* name
* description&#x20;
* compliance\_result
  * `not_assessed`
  * `partially_compliant`
  * `non_compliant`
  * `compliant`
  * `not_applicable`
* requirement\_progress
  * `to_do`
  * `in_progress`
  * `in_review`
  * `done`
* score
  * integer from `0 to 100`
* observations

### Special considerations

* The wizard will attempt to match based on the ref\_id and fallback to the urn otherwise. If none could be used, the row will be skipped.
* name and description columns are not used but serve as an anchor point for reference.
* Assessable will fallback to false
* Unassessable rows are skipped.



## 🐞 Findings followup (eg. pentest)

### Template

{% file src="../.gitbook/assets/sample004.xlsx" %}

### Supported fields



* ref\_id
* name\*
* description
* severity
  * `low`
  * `medium`
  * `high`
  * `critical`
* status\*
  * `identified`
  * `confirmed`
  * `dismissed`
  * `assigned`
  * `in_progress`
  * `mitigated`
  * `resolved`
  * `deprecated`
* filtering\_labels\
  you can add multiple labels for one finding separating them with `|` ( e.g. interna&#x6C;**|**&#x70;entes&#x74;**|**...)
* `priority` -integer 1–4
* `eta` - estimated resolution date (YYYY-MM-DD)
* `due_date` - due date (YYYY-MM-DD)
* `observation`&#x20;



## 👥 Users

### Template

{% file src="../.gitbook/assets/sample005.xlsx" %}

### **Supported fields**



* email\*
* first\_name
* last\_name



## ☣️ Risk assessment&#x20;

The risk assessment is an advanced object that needs special considerations. Make sure to pick the matrix that will be used to map your labels to the values on CISO Assistant. If you have a specific matrix, you should start by including it as a custom library.

inherent\_level, current\_level and residual\_level are kept on the excel sample just for visual aid. The application computes them based on impact and probability  to ensure consistency with the matrix definition.

Controls are created on picked based on the perimeter's domain. Line breaks are used as seperator.

### Template:

{% file src="../.gitbook/assets/risk_assessment_template.xlsx" %}

### Supported fields:

* ref\_id : String
* name\* : String
* description : String
* inherent\_impact : String<sup>1</sup>
* inherent\_proba : String<sup>1</sup>
* _existing\_controls :_ String
* current\_impact : String<sup>1</sup>
* current\_proba : String<sup>1</sup>
* _additional\_controls :_ String
* residual\_impact : String<sup>1</sup>
* residual\_proba : String<sup>1</sup>
* treatment : String
  * open
  * mitigate
  * accept
  * avoid
  * transfer

(1): the string of characters must represent a value present in the chosen risk matrix



## 🏢 Business Impact Analysis

The BIA export/import uses a **multi-sheet Excel file**:

* **Summary** sheet - one row per BIA
* **\<BIA name>** sheet - one row per asset assessment for that BIA
* **\<BIA name> - thresholds** sheet - one row per escalation threshold for that BIA

### Template

{% file src="../.gitbook/assets/sample_business_impact_analysis (1).xlsx" %}

***

### Summary sheet

#### Supported fields

* `name`\*
* `description`
* `perimeter` - name of the perimeter
* `perimeter_ref_id` - ref\_id of the perimeter
* `risk_matrix` - name of the risk matrix
* `risk_matrix_ref_id` - ref\_id of the risk matrix&#x20;
* `folder` - domain/folder name
* `version`
* `status`
  * `planned`
  * `in_progress`
  * `in_review`
  * `done`
  * `deprecated`
* `eta` - estimated completion date
* `due_date`
* `observation`
* `authors` - comma-separated list of user emails
* `reviewers` - comma-separated list of user emails

Special considerations

* `status` defaults to `planned` if not provided
* `perimeter` and `risk_matrix` are resolved by UUID, ref\_id, or name (in that order)
* `authors` and `reviewers` are matched by email address

***

### Asset assessment sheets (\<BIA name>)

One sheet per BIA, named after the BIA. Each row is an asset assessment.

Supported fields

* `bia_name`\* - name of the parent BIA (injected automatically on re-import)
* `asset`\* - name of the asset
* `asset_ref_id` - ref\_id of the asset (alternative lookup)
* `recovery_documented` - `true` / `false`
* `recovery_tested` - `true` / `false`
* `recovery_targets_met` - `true` / `false`
* `dependencies` - comma-separated list of asset names or ref\_ids
* `associated_controls` - comma-separated list of applied control names or ref\_ids
* `evidences` - comma-separated list of evidence names
* `observation`

Special considerations

* `asset` is resolved by UUID, ref\_id, or name (in that order)
* Boolean fields accept `true/false`, `yes/no`, `1/0`
* Multiple values (dependencies, controls, evidences) use comma separation

***

### Threshold sheets (\<BIA name> - thresholds)

One sheet per BIA, named `<BIA name> - thresholds`. Each row is an escalation threshold.

#### Supported fields

* `bia_name`\* - name of the parent BIA
* `asset`\* - name of the asset (used to resolve the asset assessment)
* `asset_ref_id` - ref\_id of the asset (alternative lookup)
* `point_in_time`\* - integer (time horizon in hours/days depending on your matrix)
* `quali_impact` - integer qualitative impact level (-1 = not set)
* `quanti_impact` - decimal quantitative impact value
* `quanti_impact_unit` - unit for quantitative impact (e.g. `currency`)
* `qualifications` - comma-separated list of qualification names
* `justification`

Special considerations

* The asset assessment is resolved by matching `(bia_name, asset)` — both must already exist before thresholds are imported
* `point_in_time` combined with the asset assessment forms the unique key for update/deduplication
* `quali_impact` defaults to `-1` (not set) if blank
* `quanti_impact` defaults to `0` if blank

## ⚙️  Elementary actions

Elementary actions are useful to model a killchain during the 4th workshop of an EBIOS RM study.&#x20;

### Supported fields:

* ref\_id
* name\*
* description&#x20;
* attack\_stage\*
  * (in English)
    * know
    * enter
    * _discover_
    * _exploit_
  * (in F&#x72;_&#x65;nch)_
    * _connaitre_
    * _entrer_
    * _trouver_
    * _exploiter_
* icon
  * _server_
  * _computer_
  * _cloud_
  * _file_
  * _diamond_
  * _phone_
  * _cube_
  * _blocks_
  * _shapes_
  * _network_
  * _database_
  * _key_
  * _search_
  * _carrot_
  * _money_
  * _skull_
  * _globe_
  * _usb_
* domain

{% file src="../.gitbook/assets/sample007.xlsx" %}



## Reference controls

\
Reference controls are templates of the controls to apply.&#x20;

### Supported fields:

* ref\_id
* name
* description&#x20;
* category
* function
* domain

{% file src="../.gitbook/assets/sample_reference_controls.xlsx" %}

Reference controls can be bundled also as a library.



## Threats



* ref\_id
* name
* description&#x20;
* domain

{% file src="../.gitbook/assets/sample_threats.xlsx" %}



## Third parties ecosystems

Adding entities, solutions and contracts go through the same file to be able to keep consistent relationships. Each concept needs to be on a separate tab of the excel sheet.<br>

{% file src="../.gitbook/assets/third_parties_ecosystem_template (1).xlsx" %}

The file has to be divided into 3 sheets namely "Entities", "Solutions" and "Contracts"

### Supported fields

<mark style="color:$danger;">\*</mark><mark style="color:$info;">:  Required fields</mark>

#### Entities

* `ref_id`&#x20;
* `name` <mark style="color:$danger;">\*</mark>
* `description`
* `mission`
* `country` (Country code [https://en.wikipedia.org/wiki/ISO\_3166-1\_alpha-2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2))
* `currency`  (ISO 4217 format [https://en.wikipedia.org/wiki/ISO\_4217](https://en.wikipedia.org/wiki/ISO_4217))
* `parent_entity_id`
* `dependency`(Integer in \[0,4])
* `penetration` (Integer in \[0,4])
* `maturity`  (Integer in \[1,4])
* `trust`  (Interger in \[1,4])
* `domain` <mark style="color:$danger;">\*</mark>

#### Solutions

* `ref_id`
* `name` <mark style="color:$danger;">\*</mark>
* `description`
* `provider_entity_ref_id` <mark style="color:$danger;">\*</mark>
* `criticality`  (Integer in \[1,4])

#### Contracts

* `ref_id`
* `name` <mark style="color:$danger;">\*</mark>
* `description`
* `provider_entity_ref_id`
* `solution_ref_id`
* `status`  can be `draft` , `active`,`expired` or `terminated`
* `start_date` (YYY-MM-DD format [https://en.wikipedia.org/wiki/ISO\_8601](https://en.wikipedia.org/wiki/ISO_8601))
* `end_date` (YYY-MM-DD format [https://en.wikipedia.org/wiki/ISO\_8601](https://en.wikipedia.org/wiki/ISO_8601))
* `annual_expense`
* `currency` (ISO 4217 format [https://en.wikipedia.org/wiki/ISO\_4217](https://en.wikipedia.org/wiki/ISO_4217))
* `domain`
* `lei`
* `euid`
* `vat`
* `duns`

## Processings

### Template

{% file src="../.gitbook/assets/sample-processings (1).xlsx" %}

### Supported fields

* ref\_id
* name\*
* description
* status
  * Approved
  * Draft
  * In review
  * Deprecated
* processing\_nature
* domain
* assigned\_to
* labels
* dpia\_required
  * FALSE
  * TRUE
* dpia\_reference



## Policies

{% file src="../.gitbook/assets/policies_template.xlsx" %}

### Supported fields

* ref\_id
* name
* description
* domain
* status
* link
* `csf_function` - defaults to `govern`
  * `govern`
  * `identify`
  * `protect`
  * `detect`
  * `respond`
  * `recover`
* `priority`&#x20;
  * integer 1–4
* `effort`&#x20;
  * size estimate: `XS`, `S`, `M`, `L`, `XL`
* `eta`&#x20;
  * estimated completion date (YYYY-MM-DD)
* `expiry_date`&#x20;
  * expiry date (YYYY-MM-DD)
* `filtering_labels`&#x20;
  * pipe- or comma-separated label names (created if missing

## Exceptions

{% file src="../.gitbook/assets/exceptions_template.xlsx" %}

### Supported fields

* ref\_id
* name
* description
* domain
* status
  * draft, in\_review, approved, resolved, expired, deprecated
* severity
  * undefined, info, low, medium, high, critical
* expiration\_date
  * YYYY-MM-DD
* observation

## Incidents

{% file src="../.gitbook/assets/incidents_template.xlsx" %}

### Supported fields

* ref\_id
* name
* description
* domain
* status
  * new, ongoing, resolved, closed, dismissed
* severity
  * critical/sev1(1), major/sev2(2), moderate/sev3(3), minor/sev4(4), low/sev5(5), unknown(6)
* detection
  * internal/internally\_detected, external/externally\_detected
* reported\_at
  * DateTime
* `link`&#x20;
  * URL reference
* `filtering_labels`&#x20;
  * pipe- or comma-separated label names (created if missing)



## Vulnerability

###

{% file src="../.gitbook/assets/template_vulnerabilities.xlsx" %}

### Supported fields

* ref\_id
* name\*
* description
* status
  * Potential
  * Exploitable
  * Mitigated
  * Not exploitable
  * Fixed
  * Unaffected
* severity
  * Information
  * Low
  * Medium
  * High
  * Critical
* assets (newline-separated list of the name of the assets)
* applied\_controls (newline-separated of the names)
* security\_exceptions (newline-separated of the names)



## 📁 Folders

Folders (domains) are the top-level organisational units in CISO Assistant. Importing them lets you pre-populate a domain hierarchy before importing other objects.

#### Supported fields

* `name`\*
* `description`
* `domain` - name of the parent folder, must match exactly one existing folder name (case-insensitive)

### Template

{% file src="../.gitbook/assets/sample_folders.xlsx" %}

#### Special considerations

* Conflict detection is performed by `name` + parent folder.
* When `domain` is left blank the folder is attached to the root of the tenant.
* An error is returned if `domain` matches more than one folder name.

***

## ✅ Tasks (incoming)

Tasks in CISO Assistant are modelled as **TaskTemplates** (definitions) with **TaskNodes** (individual occurrences). A non-recurrent task has one node; recurrent tasks generate one node per scheduled occurrence.

The wizard imports both in a single multi-sheet Excel file: a **Summary** sheet for the templates, plus one sheet per template that contains its past occurrences. A flat CSV upload is also accepted and imports templates only.

#### Template

{% file src="../.gitbook/assets/sample_task-templates.xlsx" %}

#### Supported fields — Summary sheet

* `ref_id` — reference identifier; used as the primary conflict-detection key when present
* `name`\*
* `description`
* `folder` — folder name; falls back to the domain selected in the wizard
* `is_recurrent`
  * `true` / `yes` / `1`
  * `false` / `no` / `0`
* `enabled`
  * `true` / `yes` / `1` (default)
  * `false` / `no` / `0`
* `link` - URL
* `task_date`  (YYYY-MM-DD)
* `assigned_to` - comma-separated list of user emails and/or team names
* `assets` - comma-separated asset names or ref\_ids
* `applied_controls` - comma-separated control names or ref\_ids
* `evidences` - comma-separated evidence names
* `compliance_assessments` - comma-separated assessment names; the `name - version` format produced by the export is accepted
* `risk_assessments` - comma-separated assessment names; the `name - version` format produced by the export is accepted
* `findings_assessment` - comma-separated findings assessment names
* `status` - non-recurrent only; sets the status of the single task node
  * `pending`
  * `in_progress`
  * `completed`
  * `cancelled`
* `observation` - free-text; non-recurrent only
* `schedule_frequency` - recurrent only
  * `DAILY`
  * `WEEKLY`
  * `MONTHLY`
  * `YEARLY`
* `schedule_interval` - integer; repeat every N periods (recurrent only)
* `schedule_days_of_week` - comma-separated integers 1–7 (Mon=1, Sun=7), WEEKLY only
* `schedule_weeks_of_month` - comma-separated integers -1–4 (1=first, -1=last)
* `schedule_months_of_year` - comma-separated integers 1–12, YEARLY only
* `schedule_end_date` - date (YYYY-MM-DD)
* `schedule_occurrences` - integer; stop after N occurrences
* `schedule_overdue_behavior`
  * `DELAY_NEXT`
  * `NO_IMPACT`

#### Supported fields - per-template node sheets

Each sheet is named `N-template name` (truncated to 31 characters) and contains one row per past occurrence.

* `due_date`\* - date (YYYY-MM-DD); rows with a future date are skipped automatically
* `scheduled_date` - date (YYYY-MM-DD); defaults to `due_date` when blank
* `status`
  * `pending`
  * `in_progress`
  * `completed`
  * `cancelled`
* `observation`&#x20;

#### Special considerations

* **Folder is a fallback.** Each row's `folder` column is resolved first; the domain selected in the wizard is only used when a row has no folder.
* **Future nodes are skipped.** Rows whose `due_date` is after today are ignored - those occurrences will be regenerated automatically from the schedule.
* **Round-trip safe.** Exporting then re-importing with **Update** mode overwrites existing task nodes and templates without creating duplicates. With **Skip** mode, existing records are left unchanged.
* **Clearing relationships.** In **Update** mode, leaving a relation column (e.g. `assigned_to`, `assets`) blank in the file clears the existing links on the template.
* **CSV upload.** A CSV file is accepted and imports the Summary sheet fields only; no task nodes are processed.



