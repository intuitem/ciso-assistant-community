---
description: Import a library into CISO Assistant
---

# Import a library

You can upload an Excel workbook directly. CISO Assistant converts it during import, so you do not need to create a YAML file first. If you already have a YAML library, you can upload that instead.

## Upload a library

1. In CISO Assistant, open **Governance > Libraries**.
2. Click on the <img src="../../.gitbook/assets/import_library_button.png" alt="Purple button with a white file in it and a &#x22;+&#x22; sign" data-size="line"> button.
3. Select your Excel (`.xlsx`) workbook or `.yaml` library and upload it. Your library will be automatically loaded into your instance.

![Libraries page with Governance > Libraries selected and the upload button highlighted in the upper right](../../.gitbook/assets/import_library.png)

If the file is valid, CISO Assistant confirms the import. The loaded frameworks become available under **Catalog > Frameworks**. Other loaded library objects are available in their corresponding areas.

If the import reports an error, correct the source file and try again. See [Excel file anatomy](excel-file-anatomy.md) and [Create a library with Excel](create-library-with-excel.md) for help preparing the Excel file, or [Test a library](test-library.md) to check an imported framework.

### Optional: convert Excel to YAML first

Pre-conversion is not required, but if you want to generate or inspect the YAML yourself, run [`convert_library_v2.py`](https://github.com/intuitem/ciso-assistant-community/blob/main/backend/scripts/convert_library_v2.py) from the repository root:

```shell
python backend/scripts/convert_library_v2.py path/to/library.xlsx
```

Then upload the generated `.yaml` file using the same <img src="../../.gitbook/assets/import_library_button.png" alt="Purple button with a white file in it and a &#x22;+&#x22; sign" data-size="line"> button.
