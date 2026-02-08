---
description: Importing CIS Controls or CSA CCM
---

# CIS Controls / Cloud Controls Matrix (CCM)

{% hint style="warning" %}
**NOTE:** This section is still under reworking. For complementary informations, please refer to the [**dedicated README on GitHub for CIS Controls**](https://github.com/intuitem/ciso-assistant-community/blob/main/tools/excel/cis/README.md) or the [**dedicated README on GitHub for CCM**](https://github.com/intuitem/ciso-assistant-community/blob/main/tools/excel/ccm/README.md).
{% endhint %}

Since CSA and CIS have more restrictive terms on their licenses, users need to perform an extra action by downloading the sheet on their side and running the preparation script as described in the tools folder.

To import the CIS Controls, you need to prepare the file first. The easy way, once you have python and the [`convert_library_v2.py` depdencencies installed](designing-your-own-libraries.md#prerequisites), is to copy the Excel sheet as-is (`CIS_Controls_Version_8.xlsx`) into the tools folder and run `convert_cis.sh` for Linux/Mac, or `convert_cis.bat` for Windows.



CIS controls converter can be found under [`tools/excel/cis`](https://github.com/intuitem/ciso-assistant-community/tree/main/tools/excel/cis)

CCM converter can be found under [`tools/excel/ccm`](https://github.com/intuitem/ciso-assistant-community/tree/main/tools/excel/ccm)



Afterwards, you can upload the generated yaml file as a custom library and load it.



Alternatively, you can run the prep script first (`tools/cis/prep_cis.py`) and mention any short string as the packager and then pass the new Excel sheet to the `convert_library_v2.py`
