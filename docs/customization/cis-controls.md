---
description: importing CIS Controls
---

# CIS Controls

Since CSA and CIS have more restrictive terms on their licenses, users need to perform an extra action by downloading the sheet on their side and running the preparation script as described in the tools folder.

To import the CIS Controls, you need to prepare the file first. The easy way, once you have python and the conver\_library depdencencies installed, is to copy the Excel sheet as-is (`CIS_Controls_Version_8.xlsx`) into the tools folder and run `convert_cis.sh`



Afterwards, you can upload the generated yaml file as a custom library and load it.



Alternatively, you can run the prep script first (`cis/prep_cis.py`) and mention any short string as the packager and then pass the new Excel sheet to the `convert_library.py`
