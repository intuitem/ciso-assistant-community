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

### Generate a Framework workbook

1. Make a copy of [`prepare_framework_v2_config.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/prepare_framework_v2_config.xlsx). Read the `info` sheet, then replace the example values in the `base` sheet with your own. For a first Framework, `base` is enough: leave the optional rows and sheets starting with `#` disabled.
2. From the CISO Assistant repository root, run [`prepare_framework_v2.py`](https://github.com/intuitem/ciso-assistant-community/blob/main/tools/prepare_framework_v2.py) with your configuration file:

   ```shell
   python tools/prepare_framework_v2.py --input path/to/your-config.xlsx --output path/to/your-library.xlsx
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

If you choose to check the workbook, run [`check_library_v2.py`](https://github.com/intuitem/ciso-assistant-community/blob/main/tools/check_library_v2.py) from the repository root:

```shell
python tools/check_library_v2.py path/to/your-library.xlsx
```

If the check reports an error, correct the workbook and run it again.

## 5. Optional: convert the workbook to YAML

You do not need to convert the Excel file before importing it into CISO Assistant. If you want to inspect the resulting YAML, run [`convert_library_v2.py`](https://github.com/intuitem/ciso-assistant-community/blob/main/backend/scripts/convert_library_v2.py) from the repository root:

```shell
python backend/scripts/convert_library_v2.py path/to/your-library.xlsx
```

By default, the script creates a `.yaml` file in the current directory with the same base name as the Excel file. For example, `example_framework.xlsx` becomes `example_framework.yaml`.

## 6. Import the library

Follow [Import a library](import-library.md) to upload the Excel workbook, or the YAML file if you converted it.
