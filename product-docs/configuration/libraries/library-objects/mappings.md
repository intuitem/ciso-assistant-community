---
description: Link requirements from two frameworks
---

# Mappings

A Mapping describes how requirements from one [Framework](framework.md) relate to requirements from another. The two frameworks can be in different libraries, and the Mapping does not need their Excel sheets in its own workbook.

## Excel structure and fields

A Mapping object uses two sheets:
* `<object>_meta` describes the object.
* `<object>_content` lists the requirement links.

For example, if `mappings` is the object prefix, the sheets are `mappings_meta` and `mappings_content`.

An asterisk (<mark style="color:$danger;">*</mark>) marks a required field.

### `<object>_meta`

The metadata sheet is a key-value table with one property per row.

| Property | Meaning | Format / allowed values |
| --- | --- | --- |
| `type`<mark style="color:$danger;">*</mark> | Identifies the object type | Enter `requirement_mapping_set` |
| `urn`<mark style="color:$danger;">*</mark> | Unique identifier of the Mapping | `urn:<packager>:risk:req_mapping_set:<identifier>` |
| `ref_id`<mark style="color:$danger;">*</mark> | Short identifier of the Mapping | Letters, numbers, `.`, `_`, or `-` only; no spaces. Keep it stable across versions |
| `name`<mark style="color:$danger;">*</mark> | Name shown to users | Text |
| `description`<mark style="color:$danger;">*</mark> | What the Mapping covers | Text |
| `source_framework_urn`<mark style="color:$danger;">*</mark> | Framework being mapped from | Full Framework URN: `urn:<packager>:risk:framework:<identifier>` |
| `target_framework_urn`<mark style="color:$danger;">*</mark> | Framework being mapped to | Full Framework URN: `urn:<packager>:risk:framework:<identifier>` |
| `source_node_base_urn`<mark style="color:$danger;">*</mark> | Prefix for source requirement URNs | The source Framework's `base_urn` |
| `target_node_base_urn`<mark style="color:$danger;">*</mark> | Prefix for target requirement URNs | The target Framework's `base_urn` |

### `<object>_content`

The content sheet contains one row per requirement link. The converter combines each node ID with the corresponding node base URN from the metadata sheet.

| Field | Meaning | Format / allowed values |
| --- | --- | --- |
| `source_node_id`<mark style="color:$danger;">*</mark> | Requirement identifier in the source Framework | URN suffix of the source requirement, without its `base_urn` |
| `target_node_id`<mark style="color:$danger;">*</mark> | Requirement identifier in the target Framework | URN suffix of the target requirement, without its `base_urn` |
| `relationship`<mark style="color:$danger;">*</mark> | How the source requirement compares with the target | `subset`, `intersect`, `equal`, `superset`, or `not_related` |
| `rationale` | Basis for the comparison | `syntactic`, `semantic`, or `functional` |
| `strength_of_relationship` | Optional strength assigned to the link | Whole number |

{% hint style="info" %}
Use the identifier that appears at the end of the requirement's URN. It is often based on its `ref_id`, but the two can differ, so check the Framework you are mapping.
{% endhint %}

## Relationships with other objects

A Mapping refers to two [Frameworks](framework.md) by URN and links their requirement nodes. It is independent of their sheet pairs: neither Framework has to be defined in the Mapping library. If those Frameworks come from other libraries, list the libraries under `dependencies` in [Library metadata](library-metadata.md).

## Tips

### When creating a library

- Check the source and target Framework URNs and node base URNs before entering requirement links
- Write each relationship from source to target; the reverse Mapping is generated during conversion

### When updating a library

- Keep the Mapping `urn` and `ref_id` stable when only its wording changes
- Review requirement links if either Framework changes a requirement URN

## Example

The tables below show an example of a Mapping from one Framework version to another.

### `mappings_meta`

| Property | Value |
| --- | --- |
| `type` | `requirement_mapping_set` |
| `urn` | `urn:intuitem:risk:req_mapping_set:sample-framework.1-to-2` |
| `ref_id` | `sample-framework.1-to-2` |
| `name` | Sample framework version mapping |
| `description` | Links selected requirements from version 1 to version 2 |
| `source_framework_urn` | `urn:intuitem:risk:framework:sample-framework.1` |
| `target_framework_urn` | `urn:intuitem:risk:framework:sample-framework.2` |
| `source_node_base_urn` | `urn:intuitem:risk:req_node:sample-framework.1` |
| `target_node_base_urn` | `urn:intuitem:risk:req_node:sample-framework.2` |

### `mappings_content`

| source_node_id | target_node_id | relationship | rationale |
| --- | --- | --- | --- |
| `access.1` | `access.1` | `equal` | `semantic` |
| `access.2` | `access.2` | `subset` | `semantic` |

To see an example of Mappings in a complete Excel file, download [`mapping-iso27001-2013-to-iso27001-2022.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/excel/iso27001/mapping-iso27001-2013-to-iso27001-2022.xlsx) and open its `mappings_meta` and `mappings_content` sheets.

## Advanced: YAML representation of this object

This section is mainly for advanced users and debugging. The excerpt below shows how the Mappings from the tables above can appear after import. Conversion creates a forward and a reverse Mapping.

<details>
<summary>Show YAML</summary>

```yaml
objects:
  requirement_mapping_sets:
  - urn: urn:intuitem:risk:req_mapping_set:sample-framework.1-to-2
    ref_id: sample-framework.1-to-2
    name: Sample framework version mapping
    description: Links selected requirements from version 1 to version 2
    source_framework_urn: urn:intuitem:risk:framework:sample-framework.1
    target_framework_urn: urn:intuitem:risk:framework:sample-framework.2
    requirement_mappings:
    - source_requirement_urn: urn:intuitem:risk:req_node:sample-framework.1:access.1
      target_requirement_urn: urn:intuitem:risk:req_node:sample-framework.2:access.1
      relationship: equal
      rationale: semantic
    - source_requirement_urn: urn:intuitem:risk:req_node:sample-framework.1:access.2
      target_requirement_urn: urn:intuitem:risk:req_node:sample-framework.2:access.2
      relationship: subset
      rationale: semantic
  - urn: urn:intuitem:risk:req_mapping_set:sample-framework.1-to-2-revert
    ref_id: sample-framework.1-to-2-revert
    name: Sample framework version mapping
    description: Links selected requirements from version 1 to version 2
    source_framework_urn: urn:intuitem:risk:framework:sample-framework.2
    target_framework_urn: urn:intuitem:risk:framework:sample-framework.1
    requirement_mappings:
    # ...
    - source_requirement_urn: urn:intuitem:risk:req_node:sample-framework.2:access.2
      target_requirement_urn: urn:intuitem:risk:req_node:sample-framework.1:access.2
      relationship: superset
      rationale: semantic
```

The reverse Mapping swaps source and target. A `subset` relationship becomes `superset` in that direction.
</details>

## Related pages

- [Library objects](README.md)
- [Framework](framework.md)
- [Excel examples](../examples.md)
- [Create a library with Excel](../create-library-with-excel.md)
- [Import a library](../import-library.md)
- [Update a library](../update-library.md)
