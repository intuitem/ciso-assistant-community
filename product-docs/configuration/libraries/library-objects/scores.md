---
description: Define score levels for a framework
---

# Scores

Scores give names and descriptions to the numeric levels used by a [Framework](framework.md). They are optional: a framework can set `min_score` and `max_score` without a Scores sheet.

## Excel structure and fields

A Scores object uses two sheets:
* `<object>_meta` describes the object.
* `<object>_content` lists its levels.

For example, if `scr` is the object prefix, the sheets are `scr_meta` and `scr_content`.

An asterisk (<mark style="color:$danger;">*</mark>) marks a required field. <mark style="color:$info;">T</mark> marks a field that supports translations.

### `<object>_meta`

The metadata sheet is a key-value table with one property per row.

| Property | Meaning | Format / allowed values |
| --- | --- | --- |
| `type`<mark style="color:$danger;">*</mark> | Identifies the object type | Enter `scores` |
| `name`<mark style="color:$danger;">*</mark> | Defines the object prefix used to name its sheet pair and link it to a framework | The sheet name prefix (e.g., `scr`). Do not include `_meta` or `_content`. |

For example, if `name` is `scr`, the object is defined by `scr_meta` and `scr_content`. You will need to set the framework's `scores_definition` property to the same prefix.

### `<object>_content`

The content sheet contains one row per score level.

| Field | Meaning | Format / allowed values |
| --- | --- | --- |
| `score`<mark style="color:$danger;">*</mark> | Numeric value of the level | Unique whole number, zero or greater |
| `name`<mark style="color:$danger;">*</mark> <mark style="color:$info;">T</mark> | Label shown for that value | Text |
| `description` <mark style="color:$info;">T</mark> | Short explanation of the level | Text |
| `description_doc` <mark style="color:$info;">T</mark> | Additional explanation associated with the level | Text |

See [Translate library content](../translations.md) for how to add translations.

## Relationships with other objects

Set `scores_definition` in a [Framework](framework.md) metadata sheet to the Scores object prefix. A framework requirement can use another scale by putting its prefix in the framework content's `scores_definition` column. Answer choices in [Answers](answers.md) can contribute points through `add_score`.

## Tips

### When creating a library

- Define the numeric range in the framework's `min_score` and `max_score` properties, then add labels for the levels users need to interpret
- Use a separate Scores object for a requirement only when its scale genuinely differs from the framework's main scale

### When updating a library

- Keep score numbers stable when changing their names or descriptions
- Review existing audits before changing the range or the meaning of a score

## Example

The tables below show an example of a Scores object with three levels.

### `scr_meta`

| Property | Value |
| --- | --- |
| `type` | `scores` |
| `name` | `scr` |

### `scr_content`

| score | name | description |
| --- | --- | --- |
| `0` | Not met | The requirement is not met |
| `1` | Partly met | Some parts of the requirement are met |
| `2` | Met | The requirement is met |

To see an example of Scores in a complete Excel file, download [`example_framework.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/example_framework.xlsx) and open its `scr_meta` and `scr_content` sheets. That workbook also has a second scale in `scr_binary_meta` and `scr_binary_content`.

## Advanced: YAML representation of this object

This section is mainly for advanced users and debugging. The excerpt below shows how the Scores from the tables above can appear inside a [Framework](framework.md) after import.

<details>
<summary>Show YAML</summary>

```yaml
objects:
  framework:
    urn: urn:intuitem:risk:framework:sample-framework.1
    # ...
    min_score: 0
    max_score: 2
    scores_definition:
    - score: 0
      name: Not met
      description: The requirement is not met
    - score: 1
      name: Partly met
      description: Some parts of the requirement are met
    - score: 2
      name: Met
      description: The requirement is met
```

When a requirement uses an alternative scale, the YAML stores that scale under `scores_definition.alternatives` and gives the requirement a `scores_definition_ref`.
</details>

## Related pages

- [Library objects](README.md)
- [Framework](framework.md)
- [Answers](answers.md)
- [Excel examples](../examples.md)
- [Translate library content](../translations.md)
- [Create a library with Excel](../create-library-with-excel.md)
- [Import a library](../import-library.md)
- [Update a library](../update-library.md)
