---
description: Shorten threat and reference control URNs in a framework workbook
---

# URN Prefixes

URN Prefixes let you use short references in a [Framework](framework.md) instead of repeating a full URN for every Threat or Reference Control. They help when several requirements refer to objects from the same catalogue. A URN Prefixes object is optional and has no use on its own.

## Excel structure and fields

A URN Prefix object uses two sheets:
* `<object>_meta` describes the object.
* `<object>_content` lists the prefixes.

For example, if `urn_pref` is the object prefix, the sheets are `urn_pref_meta` and `urn_pref_content`.

An asterisk (<mark style="color:$danger;">*</mark>) marks a required field.

### `<object>_meta`

The metadata sheet is a key-value table with one property per row.

| Property | Meaning | Format / allowed values |
| --- | --- | --- |
| `type`<mark style="color:$danger;">*</mark> | Identifies the object type | Enter `urn_prefix` |

There is no `name` property here. The converter reads prefixes from any sheet pair whose metadata type is `urn_prefix`.

### `<object>_content`

The content sheet contains one row per URN prefix. Each row pairs a short identifier with the beginning of a URN.

| Field | Meaning | Format / allowed values |
| --- | --- | --- |
| `prefix_id`<mark style="color:$danger;">*</mark> | Short identifier used before a colon in the framework | Unique text or number within this sheet |
| `prefix_value`<mark style="color:$danger;">*</mark> | URN prefix that replaces the identifier | A unique Threat or Reference Control URN prefix beginning with `urn:` |

## Relationships with other objects

In the `threats` or `reference_controls` column of a [Framework](framework.md), write `prefix_id:ref_id`. Here, `prefix_id` identifies the catalogue's URN prefix, and `ref_id` identifies a Threat or Reference Control in that catalogue. The converter combines them into the object's full URN.

The referenced object does not have to be in the same library. If it belongs to another library, add that library under `dependencies` in [Library metadata](library-metadata.md).

## Tips

### When creating a library

- Add prefixes only for catalogues you actually reference in the framework.
- Choose short, distinct `prefix_id` values so references remain easy to read.

### When updating a library

- Check that an external catalogue still uses the same URN before changing its reference.

## Example

The tables below show an example of a URN Prefixes object for two catalogues.

### `urn_pref_meta`

| Property | Value |
| --- | --- |
| `type` | `urn_prefix` |

### `urn_pref_content`

| prefix_id | prefix_value |
| --- | --- |
| `1` | `urn:intuitem:risk:threat:sample-framework.1` |
| `2` | `urn:intuitem:risk:function:sample-framework.1` |

With these prefixes, `1:t1` in a framework becomes `urn:intuitem:risk:threat:sample-framework.1:t1` after conversion. To see an example of URN Prefixes in a complete Excel file, download [`example_framework.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/example_framework.xlsx) and open its `urn_pref_meta`, `urn_pref_content`, and `fwk_content` sheets.

## Advanced: YAML representation of this object

This section is mainly for advanced users and debugging. The excerpt below shows how references using the prefixes from the tables above appear within a [Framework](framework.md) in the converted YAML.

<details>
<summary>Show YAML</summary>

```yaml
objects:
  framework:
    urn: urn:intuitem:risk:framework:sample-framework.1
    # ...
    requirement_nodes:
    - urn: urn:intuitem:risk:req_node:sample-framework.1:access.1
      assessable: true
      depth: 1
      ref_id: ACCESS.1
      # ...
      threats:
      - urn:intuitem:risk:threat:sample-framework.1:t1
      reference_controls:
      - urn:intuitem:risk:function:sample-framework.1:rc1
```

The prefixes themselves do not become a separate YAML object.

</details>

## Related pages

- [Library objects](README.md)
- [Framework](framework.md)
- [Threats](threats.md)
- [Reference Controls](reference-controls.md)
- [Excel examples](../examples.md)
- [Create a Library](../create-library.md)
- [Import a library](../import-library.md)
- [Update a library](../update-library.md)
