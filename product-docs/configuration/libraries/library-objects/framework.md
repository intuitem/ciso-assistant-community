---
description: Define a framework and its requirements in a library
---

# Framework

A Framework organizes the requirements that users assess in an audit. Its rows can form a hierarchy, from broad sections to individual requirements. You can add questions, scores, and links to other library objects when they are useful.

## Excel structure and fields

A Framework object uses two sheets:
* `<object>_meta` describes the object.
* `<object>_content` lists the framework elements.

For example, if `fwk` is the object prefix, the sheets are `fwk_meta` and `fwk_content`.

An asterisk (<mark style="color:$danger;">*</mark>) marks a required field. (<mark style="color:$info;">T</mark>) marks a field that supports translations.

### `<object>_meta`

The metadata sheet is a key-value table with one property per row.

| Property | Meaning | Format / allowed values |
| --- | --- | --- |
| `type`<mark style="color:$danger;">*</mark> | Identifies the object type | Enter `framework` |
| `urn`<mark style="color:$danger;">*</mark> | Unique identifier of the framework | `urn:<packager>:risk:framework:<identifier>`; use lowercase letters, numbers, `.`, `_`, or `-` only; no spaces |
| `base_urn`<mark style="color:$danger;">*</mark> | Prefix used to build requirement URNs | `urn:<packager>:risk:req_node:<identifier>`; use lowercase letters, numbers, `.`, `_`, or `-` only; no spaces |
| `ref_id`<mark style="color:$danger;">*</mark> | Short identifier of the framework | Letters, numbers, `.`, `_`, or `-` only; no spaces |
| `name`<mark style="color:$danger;">*</mark> <mark style="color:$info;">T</mark> | Name shown to users | Text |
| `description`<mark style="color:$danger;">*</mark> <mark style="color:$info;">T</mark> | What the framework covers | Text |
| `implementation_groups_definition` | Links an [Implementation Groups](implementation-groups.md) object | The `name` value in the Implementation Groups object's metadata sheet |
| `answers_definition` | Links an [Answers](answers.md) object | The `name` value in the Answers object's metadata sheet |
| `scores_definition` | Links a [Scores](scores.md) object | The `name` value in the Scores object's metadata sheet |
| `min_score` | Lowest score available when assessing requirements | Whole number |
| `max_score` | Highest score available when assessing requirements | Whole number |

For example, if `implementation_groups_definition` is `imp_grp`, the framework uses the sheets `imp_grp_meta` and `imp_grp_content`.

The Framework's `urn` identifies the Framework itself. By default, a section or requirement with a `ref_id` gets its own URN by appending the lowercased `ref_id` to `base_urn`. For example, `ACCESS.1` with `base_urn` `urn:intuitem:risk:req_node:sample-framework.1` becomes `urn:intuitem:risk:req_node:sample-framework.1:access.1`.

### `<object>_content`

The content sheet contains one row per section or requirement. Rows follow the order of the framework, and `depth` sets their place in the hierarchy.

| Field | Meaning | Format / allowed values |
| --- | --- | --- |
| `assessable`<mark style="color:$danger;">*</mark> | Whether users assess this element | Enter `x` for an assessable requirement, leave empty for a heading |
| `depth`<mark style="color:$danger;">*</mark> | Level in the hierarchy | Positive whole number. Start with `1` and do not skip any levels (except when returning to a lower level). |
| `ref_id` | Identifier used to recognize the element| Letters, numbers, `.`, `_`, or `-` only; no spaces. Keep it stable across versions. |
| `name` <mark style="color:$info;">T</mark> | Short title | Text |
| `description` <mark style="color:$info;">T</mark> | Requirement text or explanation | Text |
| `annotation` <mark style="color:$info;">T</mark> | Additional guidance | Text |
| `typical_evidence` <mark style="color:$info;">T</mark> | Examples of evidence to look for | Text |
| `importance` | Priority of the requirement | `mandatory`, `recommended`, or `nice_to_have` |
| `weight` | Relative weight of the requirement | Positive whole number |
| `min_score` | Lowest score for a specific requirement, overriding the framework value | Whole number |
| `max_score` | Highest score for a specific requirement, overriding the framework value | Whole number |
| `scores_definition` | Alternative score scale for this requirement | Prefix of a [Scores](scores.md) sheet pair |
| `implementation_groups` | Implementation Groups used to filter the requirement | One or more [Implementation Groups](implementation-groups.md) `ref_id` values, separated by commas |
| `questions` <mark style="color:$info;">T</mark> | Questions asked when assessing a requirement | One question per line in a cell |
| `answer` | Answer set used for each question | One [Answers](answers.md) `id` for all questions, or one `id` per question on separate lines |
| `depends_on` | Choice that makes a question appear | `question_number:choice_number`, with multiple choice numbers separated by commas; `/` for none |
| `condition` | How the choices in `depends_on` are evaluated | `any` or `all`; `/` when there is no dependency |
| `threats` | Threats associated with a requirement |  Shortened Threat URN references using [URN Prefixes](urn-prefixes.md) |
| `reference_controls` | Reference Controls associated with a requirement | Shortened Reference Controls URN references using [URN Prefixes](urn-prefixes.md) |

Use at least one of `ref_id`, `name`, or `description` for each row. If you use `ref_id`, it is recommended that you choose one that remains stable, because the converter uses it to generate the element's URN.

See [Translate library content](../translations.md) for how to add translations.

{% hint style="info" %}
For a questionnaire, write questions in `fwk_content` and define their answer types and choices in [Answers](answers.md). The `depends_on` and `condition` columns are only needed for questions that appear after a previous choice. These columns are rarely used.
{% endhint %}

## Relationships with other objects

A Framework can use [Implementation Groups](implementation-groups.md), [Answers](answers.md), and [Scores](scores.md) by naming their sheet prefixes in `fwk_meta`. Its requirements can also reference [Threats](threats.md) and [Reference Controls](reference-controls.md) by using [URN Prefixes](urn-prefixes.md). If the referenced objects are in another library, list that library under `dependencies` in [Library metadata](library-metadata.md).

[Mappings](mappings.md) connect requirements from two Frameworks, but are defined in their own sheet pair. Those Frameworks do not need to be in the same library as the Mapping.

## Tips

### When creating a library

- Start with the sections and requirements you want users to assess, then set their `depth` and `assessable` values.
- Use short, stable `ref_id` values.

### When updating a library

- Keep the framework `urn`, `base_urn`, and existing requirement `ref_id` values when possible.

## Example

The tables below show an example of a Framework with one section and one assessable requirement.

### `fwk_meta`

| Property | Value |
| --- | --- |
| `type` | `framework` |
| `urn` | `urn:intuitem:risk:framework:sample-framework.1` |
| `base_urn` | `urn:intuitem:risk:req_node:sample-framework.1` |
| `ref_id` | `SAMPLE.1` |
| `name` | Sample framework |
| `description` | A short set of access management requirements |

### `fwk_content`

| assessable | depth | ref_id | name | description |
| --- | --- | --- | --- | --- |
|  | `1` | `ACCESS` | Access management |  |
| `x` | `2` | `ACCESS.1` | Review access rights | Review user access regularly |

To see an example of a Framework in a complete Excel file, download [`example_framework.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/example_framework.xlsx) and open its `fwk_meta` and `fwk_content` sheets. For questions and conditional answers, see [`example_questionnaire.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/example_questionnaire.xlsx).

## Advanced: YAML representation of this object

This section is mainly for advanced users and debugging. The excerpt below shows how the Framework from the tables above can appear in the converted YAML.

<details>
<summary>Show YAML</summary>

```yaml
objects:
  framework:
    urn: urn:intuitem:risk:framework:sample-framework.1
    ref_id: SAMPLE.1
    name: Sample framework
    description: A short set of access management requirements
    requirement_nodes:
    - urn: urn:intuitem:risk:req_node:sample-framework.1:access
      assessable: false
      depth: 1
      ref_id: ACCESS
      name: Access management
    - urn: urn:intuitem:risk:req_node:sample-framework.1:access.1
      assessable: true
      depth: 2
      parent_urn: urn:intuitem:risk:req_node:sample-framework.1:access
      ref_id: ACCESS.1
      name: Review access rights
      description: Review user access regularly
```

The Excel `base_urn` does not become a separate YAML field. It is part of each requirement's `urn`.
</details>

## Related pages

- [Library objects](README.md)
- [Implementation Groups](implementation-groups.md)
- [Answers](answers.md)
- [Scores](scores.md)
- [Excel examples](../examples.md)
- [Translate library content](../translations.md)
- [Create a library with Excel](../create-library-with-excel.md)
- [Import a library](../import-library.md)
- [Update a library](../update-library.md)
