---
description: Create a Mapping between two frameworks
---

# Create a Mapping

A Mapping links requirements from two Frameworks. Start with the YAML file version of each Framework, generate an Excel workbook with [`prepare_mapping_v2.py`](https://github.com/intuitem/ciso-assistant-community/blob/main/tools/prepare_mapping_v2.py), then complete and import it. You do not need to copy the Framework sheets into the Mapping workbook for that.

## 1. Get the two Framework YAML files

Choose which Framework is the **source** and which is the **target**. The preparation script needs a YAML library containing each Framework and its requirement nodes. If you only have Excel files, convert them to YAML first as explained in [Create a Library](create-library.md). These YAML files are inputs to the preparation script. Nonetheless, you can still import the finished Mapping as Excel.

## 2. Generate the Mapping workbook

From the CISO Assistant repository root, run:

```shell
python tools/prepare_mapping_v2.py path/to/source.yaml path/to/target.yaml
```

The first file is the source Framework, and the second is the target. The script creates a `mapping-<source>-and-<target>.xlsx` file in the current directory. It fills the library and Mapping metadata, lists the source requirements in `mappings_content`, and adds `source` and `target` sheets for reference.

## 3. Link the requirements

Open the generated workbook and work in the `mappings_content` sheet. The `source` and `target` sheets are there to help you find the requirements you want to link: compare their names and descriptions, then use their `node_id` values.

The script has already filled the `source_node_id` column in `mappings_content` with assessable source requirements. You can complete those rows or clear the pre-filled values and build your own list, without removing the header row.

To create a link, fill one row in `mappings_content` as follows:

1. In `source_node_id`, enter the requirement's `node_id` from the `source` sheet.
2. In `target_node_id`, enter the requirement's `node_id` from the `target` sheet.
3. In `relationship`, choose the type of link. The `guidelines` sheet lists the available values, such as `intersect`.

For a typical Mapping, entering `intersect` in the `relationship` column will suffice. You can put another valid value only if you need to describe a more specific relationship between the requirements.

For example, an illustrative Mapping from a sample Framework to ISO/IEC 27001:2022 could look like this:

| source_node_id | target_node_id | relationship |
| --- | --- | --- |
| `access.1` | `a.5.18` | `intersect` |
| `access.1` | `a.5.16` | `intersect` |
| `identity.1` | `a.5.16` | `intersect` |

Here, `access.1` links to two target requirements, and `a.5.16` links to two source requirements. Each link has its own row. Remove any unused rows. Every row with content must have all three fields.

See [Mappings](library-objects/mappings.md) for the meaning and accepted values of each field, including the optional `rationale` and `strength_of_relationship`.

## 4. Keep the generated metadata

The script fills `library_meta` and `mappings_meta` for you, including the Framework URNs, requirement URN prefixes, and library dependencies. You do not need to change these sheets for a standard Mapping.

{% hint style="info" %}
The script uses `intuitem` by default for `provider`, `packager`, `copyright`, and the library and Mapping URNs. You can replace it with your organization's name, but make sure you update the related URNs consistently.
{% endhint %}

## 5. Import the Mapping library

Save the completed workbook, make sure both referenced Framework libraries are available in CISO Assistant, then [import the Excel file](import-library.md). You do not need to convert the Mapping workbook to YAML first.
