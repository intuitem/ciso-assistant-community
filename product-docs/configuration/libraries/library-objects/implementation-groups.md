---
description: Define groups for organizing a framework's requirements
---

# Implementation Groups

Implementation Groups let you divide a framework's elements into as many groups as needed. A group can represent a topic, a level, a category, or another useful way to organize the framework. When creating or editing an audit, users can select one or more groups to limit the audit to a relevant subset of requirements. Requirements outside the selected groups are left out of the audit's progress and score. An element can belong to one or more groups.

Implementation Groups are optional and are only useful when linked to a framework.

## Excel structure and fields

An Implementation Groups object uses two sheets:
* `<object>_meta` describes the object.
* `<object>_content` lists the groups.

For example, if `imp_grp` is the object prefix, the sheets are `imp_grp_meta` and `imp_grp_content`.

An asterisk (<mark style="color:$danger;">*</mark>) marks a required field. (<mark style="color:$info;">T</mark>) marks a field that supports translations.

### `<object>_meta`

The metadata sheet is a key-value table with one property per row.

| Property | Meaning | Format / allowed values |
| --- | --- | --- |
| `type`<mark style="color:$danger;">*</mark> | Identifies the object type | Enter `implementation_groups` |
| `name`<mark style="color:$danger;">*</mark> | Defines the object prefix used to name its sheet pair and link it to a framework | The sheet name prefix (e.g., `imp_grp`). Do not include `_meta` or `_content`. |

For example, if `name` is `imp_grp`, the object is defined by `imp_grp_meta` and `imp_grp_content`. You will need to set the framework's `implementation_groups_definition` property to the same prefix.

### `<object>_content`

The content sheet contains one row per implementation group.

| Field | Meaning | Format / allowed values |
| --- | --- | --- |
| `ref_id`<mark style="color:$danger;">*</mark> | Unique identifier used to assign the group to framework requirements | Letters, numbers, `.`, `_`, or `-` only; no spaces. Keep it consistent with the references in the framework. |
| `name`<mark style="color:$danger;">*</mark> <mark style="color:$info;">T</mark> | Name shown to users when selecting Implementation Groups | Text |
| `description` <mark style="color:$info;">T</mark> | Optional explanation of what the group includes | Text |
| `default_selected` | Rarely used. Groups preselected when an audit is created. Users can change the selection. For questionnaires with dynamic questions, it defines which groups are selected before answers add other groups. | Enter `x` for a group that should be selected when the audit is created. Otherwise, leave the cell empty. |
| `target_score` | Rarely used. Target score proposed for new audits that select this group, instead of the framework's. When several groups are selected, the highest applies. | Number within the framework's score scale. Requires a `target_score` in the framework's metadata sheet. |

See [Translate library content](../translations.md) for how to add translations.

{% hint style="info" %}
Groups marked with `default_selected` are selected when an audit is created, so the audit starts limited to their requirements. Use it when a framework has a usual starting scope, such as a baseline level, or in a questionnaire with dynamic questions, where answers can then select more groups through `select_implementation_groups`. Otherwise, leave the column empty so new audits include every requirement.
{% endhint %}

## Relationships with other objects

An Implementation Groups object is linked to a [Framework](framework.md) in two places:

1. In the framework's metadata sheet, set `implementation_groups_definition` to the Implementation Groups object prefix (e.g., `imp_grp`).
2. In the framework's content sheet, use the `implementation_groups` column to assign one or more Implementation Group `ref_id` values to each relevant framework requirement. Separate multiple identifiers with commas.

In a questionnaire with dynamic questions, an answer choice in [Answers](answers.md) can use `select_implementation_groups` to select one or more groups by their `ref_id`. When a user chooses that answer, the associated requirements become visible.

## Tips

### When creating a library

- Use short, stable `ref_id` values.

### When updating a library

- Keep existing `ref_id` values when possible. If you change one, update every matching reference in the framework's `implementation_groups` columns.
- Update the group name or description without changing its identifier when only the wording changes.

## Example

The tables below show an example of an Implementation Groups object organized by topic.

### `imp_grp_meta`

| Property | Value |
| --- | --- |
| `type` | `implementation_groups` |
| `name` | `imp_grp` |

### `imp_grp_content`

| ref_id | name | description |
| --- | --- | --- |
| `access` | Access management | Requirements about identities and permissions |
| `incidents` | Incident response | Requirements about reporting and handling incidents |

To see an example of Implementation Groups in a complete Excel file, download [`example_framework.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/example_framework.xlsx) and open its `imp_grp_meta` and `imp_grp_content` sheets.

## Advanced: YAML representation of this object

This section is mainly for advanced users and debugging. The excerpt below shows how the Implementation Groups from the tables above can appear within a [Framework](framework.md) in the converted YAML.

<details>
<summary>Show YAML</summary>

```yaml
objects:
  framework:
    urn: urn:intuitem:risk:framework:example-framework
    # ...
    implementation_groups_definition:
    - ref_id: access
      name: Access management
      description: Requirements about identities and permissions
    - ref_id: incidents
      name: Incident response
      description: Requirements about reporting and handling incidents
    # ...
    requirement_nodes:
    - urn: urn:intuitem:risk:req_node:example-framework:req-1
      assessable: true
      depth: 1
      ref_id: REQ-1
      # ...
      implementation_groups:
      - access
    - urn: urn:intuitem:risk:req_node:example-framework:req-2
      assessable: true
      depth: 1
      ref_id: REQ-2
      # ...
      implementation_groups:
      - incidents
```

Each requirement's `implementation_groups` list refers to a `ref_id` in `implementation_groups_definition`.
</details>

## Related pages

- [Library objects](README.md)
- [Framework](framework.md)
- [Excel examples](../examples.md)
- [Translate library content](../translations.md)
- [Create a Library](../create-library.md)
- [Import a library](../import-library.md)
- [Update a library](../update-library.md)
