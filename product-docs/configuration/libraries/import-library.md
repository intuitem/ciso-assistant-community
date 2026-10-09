---
description: Import a library into CISO Assistant
---

# Import a library

You can upload an Excel workbook directly. CISO Assistant converts it during import, so you do not need to create a YAML file first. If you already have a YAML library, you can upload that instead.

## Upload a library

1. In CISO Assistant, open **Governance > Libraries**.
2. Click on the <img src="../../.gitbook/assets/import_library_button.png" alt="Purple button with a white file in it and a &#x22;+&#x22; sign" data-size="line"> button.
3. Select your Excel (`.xlsx`) workbook or `.yaml` library and upload it. A new library is automatically loaded into your instance.

![Libraries page with Governance > Libraries selected and the upload button highlighted in the upper right](../../.gitbook/assets/import_library.png)

If the file is valid, CISO Assistant confirms the import. The loaded frameworks become available under **Catalog > Frameworks**. Other loaded library objects are available in their corresponding areas.

{% hint style="info" %}
If an earlier version of the same library is already loaded, CISO Assistant only stores the new version and shows "A new version of the library has been stored. Please trigger the update to apply it." To apply it, follow [Update a library](update-library.md#update-a-library-from-the-catalog).
{% endhint %}

If the import reports an error, correct the source file and try again. See [Create a Library](create-library.md) for help preparing the Excel file.

### Optional: convert Excel to YAML first

Pre-conversion is not required. If you want to generate or inspect the YAML yourself, follow [the optional conversion step](create-library.md#id-5.-optional-convert-the-workbook-to-yaml).

Then upload the generated `.yaml` file using the same <img src="../../.gitbook/assets/import_library_button.png" alt="Purple button with a white file in it and a &#x22;+&#x22; sign" data-size="line"> button.
