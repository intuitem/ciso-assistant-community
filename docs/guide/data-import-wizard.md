---
description: '[Pro] guidelines on data import format'
icon: diagram-previous
---

# Data import wizard

## Overview



If the object supports the domain column, the wizard will attempt to add the object to it, given you have the permission to do so. If the domain is not set, the wizard will default to the  fallback domain set on the wizard form.



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
* Assessable will fallback to false
* Unassessable rows are skipped.

## 🐞 Findings followup (eg. pentest)



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
* status\*
  * `identified`
  * `confirmed`
  * `dismissed`
  * `assigned`
  * `in_progress`
  * `mitigated`
  * `resolved`
  * `deprecated`



### 👥 Users

### Template

{% file src="../.gitbook/assets/sample005.xlsx" %}

### **Supported fields**



* email\*
* first\_name
* last\_name

### ☣️ Risk assessment&#x20;



The risk assessment is an advanced object that needs special considerations. Make sure to pick the matrix that will be used to map your labels to the values on CISO Assistant. If you have a specific matrix, you should start by including it as a custom library.

inherent\_level, current\_level and residual\_level are kept on the excel sample just for visual aid. The application computes them based on impact and probability  to ensure consistency with the matrix definition.

Controls are created on picked based on the perimeter's domain. Line breaks are used as seperator.



Supported fields:



* ref\_id
* name\*
* description&#x20;
* inherent\_impact
* inherent\_proba
* _existing\_controls_
* current\_impact
* current\_proba
* _additional\_controls_
* residual\_impact
* residual\_proba

{% file src="../.gitbook/assets/sample06.xlsx" %}



### ⚙️  Elementary actions



Elementary actions are useful to model a killchain during the 4th workshop of an EBIOS RM study.&#x20;

&#x20;Supported fields:



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





### Reference controls

\
Reference controls are templates of the controls to apply. The supported  fields are:



* ref\_id
* name
* description&#x20;
* category
* function
* domain

{% file src="../.gitbook/assets/sample_reference_controls.xlsx" %}

Reference controls can be bundled also as a library.



### Threats



* ref\_id
* name
* description&#x20;
* domain

{% file src="../.gitbook/assets/sample_threats.xlsx" %}
