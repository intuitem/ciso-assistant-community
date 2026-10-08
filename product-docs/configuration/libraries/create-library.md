---
description: Create a library with the Library builder or an Excel workbook
---

# Create a Library

This guide explains how to create a library with Excel. If you want to create one without a spreadsheet, we recommend the [Library builder](../authoring/library-builder.md).

{% hint style="info" %}
Some advanced features are not available in Excel. It still supports most library features, but the format is expected to be deprecated in the future.
{% endhint %}

## 1. Start with a small library

Decide which objects you need before creating the workbook. For a first Framework, start with [Library metadata](library-objects/library-metadata.md) and the [Framework](library-objects/framework.md) itself. Add other objects only when your content needs them. The [Library objects](library-objects/README.md) page explains what each object does and how they work together.

## 2. Create the workbook

You can create the Excel workbook from scratch or use `prepare_framework_v2.py` to generate a starting point for a Framework. The script is specific to Frameworks. For other types of library, follow their [object pages](library-objects/README.md) or a dedicated workflow such as [Create a Mapping](create-mapping.md).

### Set up Python for the scripts

This setup is not required if you do not plan to use the preparation script for now. You can return to it later if you decide to generate, check, or convert a workbook with Python.

{% hint style="info" %}
If the `python` command is not recognized, use `python3` instead in the commands below. If a `.py` download opens as text in your browser, right-click and save it with the filename shown in its link.
{% endhint %}

1. Install [Python](https://www.python.org/) 3.14 or later if needed, then check its version in a terminal:

   ```shell
   python --version
   ```

2. Open a terminal in the folder where you will keep your workbook and create a virtual environment:

   ```shell
   python -m venv .venv
   ```

3. Activate it. On Windows, use PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   On macOS or Linux, use:

   ```shell
   source .venv/bin/activate
   ```

4. Install the packages needed to generate and convert the workbook:

   ```shell
   python -m pip install openpyxl PyYAML
   ```

### Generate a Framework workbook

1. Download [`prepare_framework_v2_config.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/prepare_framework_v2_config.xlsx), then download the [`prepare_framework_v2.py`](https://raw.githubusercontent.com/intuitem/ciso-assistant-community/refs/heads/main/tools/prepare_framework_v2.py) script. Save both in your working folder. You do not need to download the whole repository.
2. Read the `info` sheet of the configuration workbook, then replace the example values in `base` with your own. For a first Framework, `base` is enough: leave the optional rows and sheets starting with `#` disabled.
3. With the virtual environment active, run the script from that folder:

   ```shell
   python prepare_framework_v2.py --input prepare_framework_v2_config.xlsx --output your-library.xlsx
   ```

With the default sheet name in `base`, the script creates `library_meta`, `framework_meta`, and `framework_content`. It fills in the metadata and the content sheet's column names. You will add the Framework's sections and requirements in the next step.

{% hint style="info" %}
The script currently writes `intuitem` in the generated URNs, even if you change `packager` in the configuration. If you use your own namespace, update the related URNs consistently in the generated workbook.
{% endhint %}

### Create a workbook from scratch

For a Framework-only library, create a `library_meta` sheet and a matching pair such as `framework_meta` and `framework_content`. The [Library metadata](library-objects/library-metadata.md) and [Framework](library-objects/framework.md) pages list the fields and accepted values for these sheets. You can also look at the [Excel examples](examples.md) to see complete workbooks.

## 3. Add the content

If you are creating a Framework, fill `framework_content` (or the matching content sheet if you changed its name) with the sections and requirements from your source material. Follow the [Framework](library-objects/framework.md) page for the hierarchy, required fields, and assessable requirements.

For another kind of library, such as a standalone Threats catalogue, use the [Library objects](library-objects/README.md) pages to find the sheets and fields you need. They also explain how to add supporting objects to a Framework. You can start small and add more objects later.

## 4. Recommended: Check the workbook

{% hint style="warning" %}
This check is not mandatory. It can help detect common errors and inconsistencies, but it cannot tell whether you have chosen and organized the library's objects appropriately for your framework. You can continue to the next step without doing this step.
{% endhint %}

If you choose to check the workbook, follow [the Python setup above](#set-up-python-for-the-scripts) if you have not already done so. Click [here](https://raw.githubusercontent.com/intuitem/ciso-assistant-community/refs/heads/main/tools/check_library_v2.py) to download the [`check_library_v2.py`](https://raw.githubusercontent.com/intuitem/ciso-assistant-community/refs/heads/main/tools/check_library_v2.py) script into the same folder as your workbook. This optional script also needs `pandas`, so install it in the active virtual environment:

```shell
python -m pip install pandas
```

Then run the checker from that folder, replacing the example filename with your own:

```shell
python check_library_v2.py your-library.xlsx
```

If the check reports an error, correct the workbook and run it again.

## 5. Optional: convert the workbook to YAML

This step is only for obtaining a separate YAML version of your workbook. If you do not need one, skip to the next step. When you import the Excel file, CISO Assistant converts it to YAML automatically and loads the library for you. If you want to generate and inspect the YAML yourself, follow [the Python setup above](#set-up-python-for-the-scripts) if needed, then click [here](https://raw.githubusercontent.com/intuitem/ciso-assistant-community/refs/heads/main/backend/scripts/convert_library_v2.py) to download the [`convert_library_v2.py`](https://raw.githubusercontent.com/intuitem/ciso-assistant-community/refs/heads/main/backend/scripts/convert_library_v2.py) script into the same folder as your workbook.

With the virtual environment active, run:

```shell
python convert_library_v2.py your-library.xlsx
```

The script creates a `.yaml` file in the current directory with the same base name as the Excel workbook you chose. For example, `example_framework.xlsx` becomes `example_framework.yaml`. You can open it in a text editor to inspect the result. If the script reports an error, correct the workbook and run the command again.

## 6. Import the library

Follow [Import a library](import-library.md) to upload the Excel workbook, or the YAML file if you converted it.

## 7. Check the imported library

After the import, open the library in the Catalog and check that its objects and content appear as expected. An import can succeed even if the result is not what you intended.

If the library contains a Framework, create a test audit before using it for a real one. Check the hierarchy and assessable requirements, then try any questions, answer choices, scores, Implementation Groups, and translations you added. See [Creating your first Audit](../../guides/first-audit.md) if you need help setting one up.

If something is missing or misplaced, correct the source workbook. You can then [update the library](update-library.md), or [unload and delete it](unload-or-delete-library.md) before importing the corrected file if no audit depends on it.
