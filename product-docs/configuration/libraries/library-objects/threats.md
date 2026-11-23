---
description: Define reusable threats in a library
---

# Threats

Threats describe events or situations that could harm an organization. A library can provide a catalogue of threats that a [Framework](framework.md) can reference from its requirements.

## Excel structure and fields

A Threats object uses two sheets:
* `<object>_meta` describes the object.
* `<object>_content` lists the threats.

For example, if `thrt` is the object prefix, the sheets are `thrt_meta` and `thrt_content`.

An asterisk (<mark style="color:$danger;">*</mark>) marks a required field. (<mark style="color:$info;">T</mark>) marks a field that supports translations.

### `<object>_meta`

The metadata sheet is a key-value table with one property per row.

| Property | Meaning | Format / allowed values |
| --- | --- | --- |
| `type`<mark style="color:$danger;">*</mark> | Identifies the object type | Enter `threats` |
| `base_urn`<mark style="color:$danger;">*</mark> | Prefix used to build each threat's URN | `urn:<packager>:risk:threat:<identifier>`; use lowercase letters, numbers, `.`, `_`, or `-` only; no spaces |

### `<object>_content`

The content sheet contains one row per threat.

| Field | Meaning | Format / allowed values |
| --- | --- | --- |
| `ref_id`<mark style="color:$danger;">*</mark> | Unique identifier within this sheet | Letters, numbers, `.`, `_`, or `-` only; no spaces |
| `name`<mark style="color:$danger;">*</mark> <mark style="color:$info;">T</mark> | Name of the threat | Text |
| `description` <mark style="color:$info;">T</mark> | What could happen or what the threat involves | Text |
| `annotation` <mark style="color:$info;">T</mark> | Additional context for readers | Text |

See [Translate library content](../translations.md) for how to add translations.

## Relationships with other objects

A [Framework](framework.md) can list threat URNs in the `threats` column of its content sheet. [URN Prefixes](urn-prefixes.md) can shorten these URNs in the framework's content sheet in the Excel, while the imported YAML stores full URNs.

Threats can be packaged in a library without a Framework. If a Framework in another library references them, add the Threats library's URN to `dependencies` in the Framework library's [Library metadata](library-metadata.md) object.

## Tips

### When creating a library

- Choose a stable `base_urn` for the catalogue and give each threat a stable `ref_id`.
- As a best practice, reuse the identifier at the end of the library's `urn` for the `<identifier>` part of `base_urn`. This keeps the URNs consistent.

### When updating a library

- Keep `base_urn` and existing `ref_id` values stable.
- Update names and descriptions without changing identifiers when only the wording changes.

## Example

The tables below show an example of a Threats object.

### `thrt_meta`

| Property | Value |
| --- | --- |
| `type` | `threats` |
| `base_urn` | `urn:intuitem:risk:threat:sample-framework` |

### `thrt_content`

| ref_id | name | description |
| --- | --- | --- |
| `T1` | Unauthorized access | Someone gains access to a protected account |
| `T2` | Data loss | Important data becomes unavailable |

To see an example of Threats in a complete Excel file, download [`example_framework.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/example_framework.xlsx) and open its `thrt_meta` and `thrt_content` sheets.

## Advanced: YAML representation of this object

This section is mainly for advanced users and debugging. The excerpt below shows how the Threats from the tables above can appear in the converted YAML.

<details>
<summary>Show YAML</summary>

```yaml
objects:
  threats:
  - urn: urn:intuitem:risk:threat:sample-framework:t1
    ref_id: T1
    name: Unauthorized access
    description: Someone gains access to a protected account
  - urn: urn:intuitem:risk:threat:sample-framework:t2
    ref_id: T2
    name: Data loss
    description: Important data becomes unavailable
```

The Excel `type` marker and `base_urn` do not become separate YAML fields. `base_urn` is part of each threat's `urn`.

When a requirement references a threat, its `threats` list in the converted YAML contains the threat's full URN. The requirement stores this reference, not a copy of the threat's details.
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
