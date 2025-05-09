---
description: '[Pro] guidelines on data import format'
icon: diagram-previous
---

# Data import wizard

## Overview



If the object supports the domain column, the wizard will attempt to add the object to it, given you have the permission to do so. If the domain is not set, the wizard will default to the  fallback domain set on the wizard form.



Fields with (\*) are mandatory and don't have any supported fallback.&#x20;

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

### Special considerations

* type will default to `supporting` if not set





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



#### Template

{% file src="../.gitbook/assets/sample003.xlsx" %}

#### Supported fields

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



To avoid any mixup on the expected fields and the requirements reference, you can get a  template for the expected framework by going into `Catalog/Frameworks`

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
* Unassessable rows are skipped.

## Findings followup (eg. pentest)



### Template



{% file src="../.gitbook/assets/sample004.xlsx" %}

#### Supported fields



* ref\_id
* name\*
* description
* severity
  * `low`
  * `medium`
  * `high`
  * `critical`
* status
  * `identified`
  * `confirmed`
  * `dismissed`
  * `assigned`
  * `in_progress`
  * `mitigated`
  * `resolved`
  * `deprecated`



### Users



**Supported fields**



* email
* first\_name
* last\_name

{% file src="../.gitbook/assets/sample005.xlsx" %}





