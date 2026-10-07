---
description: Define reusable reference controls in a library
---

# Reference Controls

Reference Controls describe measures an organization can put in place. A library can provide a catalogue of reference controls that a [Framework](framework.md) can reference from its requirements.

## Excel structure and fields

A Reference Controls object uses two sheets:
* `<object>_meta` describes the object.
* `<object>_content` lists the controls.

For example, if `ref_ctrl` is the object prefix, the sheets are `ref_ctrl_meta` and `ref_ctrl_content`.

An asterisk (<mark style="color:$danger;">*</mark>) marks a required field. (<mark style="color:$info;">T</mark>) marks a field that supports translations.

### `<object>_meta`

The metadata sheet is a key-value table with one property per row.

| Property | Meaning | Format / allowed values |
| --- | --- | --- |
| `type`<mark style="color:$danger;">*</mark> | Identifies the object type | Enter `reference_controls` |
| `base_urn`<mark style="color:$danger;">*</mark> | Prefix used to build each control's URN | `urn:<packager>:risk:function:<identifier>`; use lowercase letters, numbers, `.`, `_`, or `-` only; no spaces |

### `<object>_content`

The content sheet contains one row per reference control.

| Field | Meaning | Format / allowed values |
| --- | --- | --- |
| `ref_id`<mark style="color:$danger;">*</mark> | Unique identifier within this sheet | Letters, numbers, `.`, `_`, or `-` only; no spaces |
| `name`<mark style="color:$danger;">*</mark> <mark style="color:$info;">T</mark> | Name of the control | Text |
| `category` | Kind of measure | `policy`, `process`, `technical`, `physical`, or `procedure` |
| `csf_function` | Cybersecurity function associated with the control | `govern`, `identify`, `protect`, `detect`, `respond`, or `recover` |
| `description` <mark style="color:$info;">T</mark> | What the control does | Text |
| `annotation` <mark style="color:$info;">T</mark> | Additional context for readers | Text |

See [Translate library content](../translations.md) for how to add translations.

## Relationships with other objects

A [Framework](framework.md) can list reference control URNs in the `reference_controls` column of its content sheet. [URN Prefixes](urn-prefixes.md) can shorten these URNs in the framework's content sheet in the Excel, while the imported YAML stores full URNs.

Reference Controls can be packaged in a library without a Framework. If a Framework in another library references them, add the Reference Controls library's URN to `dependencies` in the Framework library's [Library metadata](library-metadata.md) object.

## Tips

### When creating a library

- Choose a stable `base_urn` for the catalogue and give each reference control a stable `ref_id`.
- As a best practice, reuse the identifier at the end of the library's `urn` for the `<identifier>` part of `base_urn`. This keeps the URNs consistent.
- Use `category` and `csf_function` only when those classifications help users find or group controls.

### When updating a library

- Keep `base_urn` and existing `ref_id` values stable.
- Update names and descriptions without changing identifiers when only the wording changes.

## Example

The tables below show an example of a Reference Controls object.

### `ref_ctrl_meta`

| Property | Value |
| --- | --- |
| `type` | `reference_controls` |
| `base_urn` | `urn:intuitem:risk:function:sample-framework.1` |

### `ref_ctrl_content`

| ref_id | name | category | csf_function | description |
| --- | --- | --- | --- | --- |
| `RC1` | Review access rights | `process` | `protect` | Review user access on a regular basis |
| `RC2` | Test backups | `procedure` | `recover` | Check that backups can be restored |

To see an example of Reference Controls in a complete Excel file, download [`example_framework.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/example_framework.xlsx) and open its `ref_ctrl_meta` and `ref_ctrl_content` sheets.

## Advanced: YAML representation of this object

This section is mainly for advanced users and debugging. The excerpt below shows how the Reference Controls from the tables above can appear in the converted YAML.

<details>
<summary>Show YAML</summary>

```yaml
objects:
  reference_controls:
  - urn: urn:intuitem:risk:function:sample-framework.1:rc1
    ref_id: RC1
    name: Review access rights
    category: process
    csf_function: protect
    description: Review user access on a regular basis
  - urn: urn:intuitem:risk:function:sample-framework.1:rc2
    ref_id: RC2
    name: Test backups
    category: procedure
    csf_function: recover
    description: Check that backups can be restored
```

The Excel `type` marker and `base_urn` do not become separate YAML fields. `base_urn` is part of each reference control's `urn`.

When a requirement references a Reference Control, its `reference_controls` list in the converted YAML contains the control's full URN. The requirement stores this reference, not a copy of the control's details.
</details>

## Related pages

- [Library objects](README.md)
- [Framework](framework.md)
- [URN Prefixes](urn-prefixes.md)
- [Excel examples](../examples.md)
- [Translate library content](../translations.md)
- [Create a Library](../create-library.md)
- [Import a library](../import-library.md)
- [Update a library](../update-library.md)
