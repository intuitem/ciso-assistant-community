---
description: Define the identity and shared properties of a library
---

# Library metadata

Library metadata describes the library as a whole: its identity, version, main and additional languages, and publisher information. Every library Excel file must contain this object. It is not metadata for a framework or another individual object.

## Excel structure and fields

The `library_meta` worksheet is a special case: it is a single two-column key-value table, not a pair of `<object>_meta` and `<object>_content` sheets. Put each property in column A and its value in column B. Use one row per property.

An asterisk (<mark style="color:$danger;">*</mark>) marks a required property. (<mark style="color:$info;">T</mark>) marks a property that supports translations.

| Property | Meaning | Format / allowed values |
| --- | --- | --- |
| `type`<mark style="color:$danger;">*</mark> | Identifies this as library metadata | Enter `library` |
| `urn`<mark style="color:$danger;">*</mark> | The library's unique URN. Keep it unchanged when publishing a new version of the same library. | A library URN starting with `urn:`; use lowercase letters, numbers, `:`, `.`, `_`, or `-` only; no spaces |
| `version`<mark style="color:$danger;">*</mark> | The library version. Increase it whenever you publish an update | Positive whole number > 0 |
| `locale`<mark style="color:$danger;">*</mark> | The primary language of the library | Two lowercase letters from [ISO 639 Set 1](https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes#Table) (e.g., `en`, `fr`) |
| `ref_id`<mark style="color:$danger;">*</mark> | The library reference identifier | Letters, numbers, `.`, `_`, or `-` only; no spaces |
| `name`<mark style="color:$danger;">*</mark> <mark style="color:$info;">T</mark> | The library name | Text |
| `description`<mark style="color:$danger;">*</mark> <mark style="color:$info;">T</mark> | The library description | Text |
| `copyright`<mark style="color:$danger;">*</mark> | The library copyright notice | Text |
| `provider`<mark style="color:$danger;">*</mark> | The organization that provides the library's content | Text |
| `packager`<mark style="color:$danger;">*</mark> | The person or organization that packaged the library | Text |
| `labels` | Search labels for the library. The converter and CISO rewrites them in uppercase. | Separate labels with commas or line breaks. Do not include spaces within a label. |
| `dependencies` | URNs of other libraries this library depends on. Most library authors can leave this out. | Library URNs separated by commas or line breaks. Use only for specific cases. |

See [Translate library content](../translations.md) for how to add translations.

## Relationships with other objects

The `dependencies` property lists the URNs of other libraries this library relies on. It is needed in specific cases, such as when a framework uses a URN prefix to reference threats or reference controls defined in another library.

## Tips

### When creating a library

- Choose the library `urn` carefully. They identify the library and should remain stable after publication. `ref_id` offers greater flexibility, but we recommend that you align it with your URN to avoid any inconsistencies.

### When updating a library

- Increase `version` while keeping the library `urn` unchanged. This lets CISO Assistant recognize the new version and preserve references to existing content.

## Example

The table below shows an example of a completed `library_meta` sheet. Each row contains one property and its value.

| Property | Value |
| --- | --- |
| `type` | `library` |
| `urn` | `urn:intuitem:risk:library:my-framework_example.1` |
| `version` | `1` |
| `locale` | `en` |
| `ref_id` | `My-Framework_Example.1` |
| `name` | Example Framework |
| `description` | This is a demonstration framework. It outlines example policies, controls, and requirements. Designed for illustration. |
| `copyright` | © 2025 Example Organization |
| `provider` | intuitem |
| `packager` | intuitem |
| `labels` | `example_framework, framework1, my-very-cool-framework, I-LOVE-MY-FRAMEWORK` |
| `dependencies` | `urn:intuitem:risk:library:doc-pol` |
| `name[fr]` | Exemple de Framework |
| `description[fr]` | Il s'agit d'un framework de démonstration. Il présente des exemples de règles, de contrôles et d'exigences. Il est conçu pour illustrer. |

To inspect this example in Excel, download [`example_framework.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/example_framework.xlsx) and open its `library_meta` sheet.

## Advanced: YAML representation of this object

This section is mainly for advanced users and debugging. You usually only have to edit the Excel file and import it. CISO Assistant will converts it to YAML automatically during import.

<details>
<summary>Show YAML</summary>

The YAML representation of the example above looks like this. The Excel `type` marker is not included. The converter will also add `convert_library_version` and generates a `publication_date` corresponding to the date the library was converted.

```yaml
urn: urn:intuitem:risk:library:my-framework_example.1
locale: en
ref_id: My-Framework_Example.1
name: Example Framework
description: 'This is a demonstration framework. It outlines example policies, controls, and requirements. Designed for illustration.'
copyright: © 2025 Example Organization
version: 1
provider: intuitem
packager: intuitem
labels:
  - MY-VERY-COOL-FRAMEWORK
  - FRAMEWORK1
  - EXAMPLE_FRAMEWORK
  - I-LOVE-MY-FRAMEWORK
translations:
  fr:
    name: Exemple de Framework
    description: Il s'agit d'un framework de démonstration. Il présente des exemples de règles, de contrôles et d'exigences. Il est conçu pour illustrer.
dependencies:
  - urn:intuitem:risk:library:doc-pol
```

Label order may differ in the converted YAML.
</details>

## Related pages

- [Library objects](README.md)
- [Excel examples](../examples.md)
- [Excel file anatomy](../excel-file-anatomy.md)
- [Translate library content](../translations.md)
- [Create a library with Excel](../create-library-with-excel.md)
- [Import a library](../import-library.md)
- [Update a library](../update-library.md)
