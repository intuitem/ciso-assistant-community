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

The table below shows an example of a `library_meta` sheet for a security operations library.

| Property | Value |
| --- | --- |
| `type` | `library` |
| `urn` | `urn:intuitem:risk:library:security-operations.1` |
| `version` | `1` |
| `locale` | `en` |
| `ref_id` | `security-operations.1` |
| `name` | Security Operations Library |
| `description` | A framework and supporting content for assessing access management and incident response. |
| `copyright` | © 2026 intuitem |
| `provider` | intuitem |
| `packager` | intuitem |
| `labels` | `security-operations, access_management, incident.response, 24x7-monitoring` |
| `name[fr]` | Bibliothèque des opérations de sécurité |
| `description[fr]` | Un référentiel et des contenus complémentaires pour évaluer la gestion des accès et la réponse aux incidents. |

## Advanced: YAML representation of this object

This section is mainly for advanced users and debugging. The excerpt below shows how the Library metadata from the table above can appear in the converted YAML.

<details>
<summary>Show YAML</summary>

```yaml
urn: urn:intuitem:risk:library:security-operations.1
locale: en
ref_id: security-operations.1
name: Security Operations Library
description: A framework and supporting content for assessing access management and incident response.
copyright: © 2026 intuitem
version: 1
provider: intuitem
packager: intuitem
labels:
  - SECURITY-OPERATIONS
  - ACCESS_MANAGEMENT
  - INCIDENT.RESPONSE
  - 24X7-MONITORING
translations:
  fr:
    name: Bibliothèque des opérations de sécurité
    description: Un référentiel et des contenus complémentaires pour évaluer la gestion des accès et la réponse aux incidents.
```

The Excel `type` marker is not included. The converter also adds `convert_library_version` and a `publication_date` when converting the file. Label order may differ in the converted YAML.
</details>

## Related pages

- [Library objects](README.md)
- [Excel examples](../examples.md)
- [Excel file anatomy](../excel-file-anatomy.md)
- [Translate library content](../translations.md)
- [Create a library with Excel](../create-library-with-excel.md)
- [Import a library](../import-library.md)
- [Update a library](../update-library.md)
