---
description: Define scores for a framework
---

# Scores

A Scores object names and describes the scores used by a [Framework](framework.md). It is optional: a framework can set a `min_score` and a `max_score` value without a Scores sheet linked to it.

## Excel structure and fields

A Scores object uses two sheets:
* `<object>_meta` describes the object.
* `<object>_content` lists the scores.

For example, if `scr` is the object prefix, the sheets are `scr_meta` and `scr_content`.

An asterisk (<mark style="color:$danger;">*</mark>) marks a required field. (<mark style="color:$info;">T</mark>) marks a field that supports translations.

### `<object>_meta`

The metadata sheet is a key-value table with one property per row.

| Property | Meaning | Format / allowed values |
| --- | --- | --- |
| `type`<mark style="color:$danger;">*</mark> | Identifies the object type | Enter `scores` |
| `name`<mark style="color:$danger;">*</mark> | Defines the object prefix used to name its sheet pair and link it to a framework | The sheet name prefix (e.g., `scr`). Do not include `_meta` or `_content`. |

For example, if `name` is `scr`, the object is defined by `scr_meta` and `scr_content`. You will need to set the framework's `scores_definition` property to the same prefix.

### `<object>_content`

The content sheet contains one row per score.

| Field | Meaning | Format / allowed values |
| --- | --- | --- |
| `score`<mark style="color:$danger;">*</mark> | Numeric value assigned to the score | Unique non-negative integer |
| `name`<mark style="color:$danger;">*</mark> <mark style="color:$info;">T</mark> | Label shown for the score | Text |
| `description` <mark style="color:$info;">T</mark> | What the score means | Text |
| `description_doc` <mark style="color:$info;">T</mark> | Rarely used. Description for the documentation score. | Text |

See [Translate library content](../translations.md) for how to add translations.

## Relationships with other objects

A Scores object can be linked to a [Framework](framework.md) in two places:

1. In the framework's metadata sheet, set `scores_definition` to the Scores object prefix (e.g., `scr`) to define the default scale.
2. Less commonly, in the framework's content sheet, use `scores_definition` to assign a separate Scores object to a requirement that needs its own scoring scale. The requirement's `min_score` and `max_score` must match that scale's range, and the scale must define a score for every value in it.

A library can therefore contain multiple Scores objects.

Answer choices in [Answers](answers.md) can contribute points through `add_score`.

## Tips

### When creating a library

- Define the numeric range in the framework's `min_score` and `max_score` properties, then add labels that help users interpret each score.
- Use a separate Scores object for a requirement only when its scale genuinely differs from the framework's main scale.

### When updating a library

- Keep score numbers stable when changing their names or descriptions.
- Review existing audits before changing the range or the meaning of a score.

## Example

The tables below show an example of a Scores object with three possible scores.

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

This section is mainly for advanced users and debugging. The excerpt below shows how the Scores from the tables above can appear within a [Framework](framework.md) in the converted YAML.

<details>
<summary>Show YAML</summary>

```yaml
objects:
  framework:
    urn: urn:intuitem:risk:framework:sample-framework
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
- [Create a Library](../create-library.md)
- [Import a library](../import-library.md)
- [Update a library](../update-library.md)
