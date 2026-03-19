---
description: Guidelines on data import format
icon: diagram-previous
---

# Data import wizard

{% hint style="info" %}
Applicable for: Data import wizard UI (Pro) and CLI (Community or Pro)\
\
Importing existing data from excel sheets is supported on the Pro plan through the UI and CLI, and on Community edition through the dedicated CLI, not a django command. The cli is available on the cli folder with the associated instructions.\
Keep in mind that the CLI needs to reach the API as it wraps its actions around it.\
The mention to the API is regarding the fact that users on both plans can still interact with the API directly in case they have some data prep phase on their end for batch import or equivalent.
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
* reference\_link (or link)
* security\_objectives
  * confidentiality: 3,integrity: 2,availability: 1,...
* disaster\_recovery\_objectives
  * rto: 1h01m01s,rpo: 2h01m01s,mtd: 3h
* labels

### Special considerations

* type will default to `supporting` if the column does not exist



## ⚙️ Applied controls

### Template

{% file src="../.gitbook/assets/sample002 (1).xlsx" %}

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

### Special considerations

* status will default to `to_do`
* csf\_function will default to `govern`



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



{% hint style="warning" %}
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



