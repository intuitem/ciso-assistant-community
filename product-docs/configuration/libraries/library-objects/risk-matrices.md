---
description: Define a risk matrix in a library
---

# Risk Matrices

A Risk Matrix combines probability and impact to determine a risk level. Its Excel sheet defines the levels on both axes, the possible risk levels, and the grid that connects them.

## Excel structure and fields

A Risk Matrix object uses two sheets:
* `<object>_meta` describes the object.
* `<object>_content` lists the levels and grid values.

For example, if `matrix` is the object prefix, the sheets are `matrix_meta` and `matrix_content`.

An asterisk (<mark style="color:$danger;">*</mark>) marks a required field. (<mark style="color:$info;">T</mark>) marks a field that supports translations.

### `<object>_meta`

The metadata sheet is a key-value table with one property per row.

| Property | Meaning | Format / allowed values |
| --- | --- | --- |
| `type`<mark style="color:$danger;">*</mark> | Identifies the object type | Enter `risk_matrix` |
| `urn`<mark style="color:$danger;">*</mark> | Unique identifier of the matrix | `urn:<packager>:risk:matrix:<identifier>`; use lowercase letters, numbers, `.`, `_`, or `-` only; no spaces |
| `ref_id`<mark style="color:$danger;">*</mark> | Short identifier of the matrix | Letters, numbers, `.`, `_`, or `-` only; no spaces |
| `name`<mark style="color:$danger;">*</mark> <mark style="color:$info;">T</mark> | Name shown to users | Text |
| `description`<mark style="color:$danger;">*</mark> <mark style="color:$info;">T</mark> | What the matrix measures | Text |

### `<object>_content`

The content sheet contains one row per probability, impact, or risk level. Add one `grid` column per impact level. Fill those columns on probability rows with the resulting risk level IDs.

| Field | Meaning | Format / allowed values |
| --- | --- | --- |
| `type`<mark style="color:$danger;">*</mark> | Kind of level defined by the row | `probability`, `impact`, or `risk` |
| `id`<mark style="color:$danger;">*</mark> | Numeric identifier of the level within its type | Whole number |
| `color`<mark style="color:$danger;">*</mark> | Color shown for this level | Set the Excel cell's fill color if needed. The cell text can stay empty |
| `abbreviation`<mark style="color:$danger;">*</mark> <mark style="color:$info;">T</mark> | Short label for the level | Text |
| `name`<mark style="color:$danger;">*</mark> <mark style="color:$info;">T</mark> | Name of the level | Text |
| `description`<mark style="color:$danger;">*</mark> <mark style="color:$info;">T</mark> | Explanation of the level | Text |
| `grid`<mark style="color:$danger;">*</mark> | Risk level for one probability and impact combination | On probability rows, a `risk` level `id`. Repeat the `grid` column once per impact level |

The first `grid` column corresponds to the lowest impact ID, the next to the next impact ID, and so on. The converter orders probabilities and impacts by their IDs.

See [Translate library content](../translations.md) for how to add translations.

## Relationships with other objects

A Risk Matrix is an independent library object.

## Tips

### When creating a library

- List the probability and impact IDs before filling the grid, so every intersection points to a defined risk ID.
- Set colors through the Excel cell fills, not by typing a color code into the `color` column.

### When updating a library

- Keep the matrix `urn` and existing level IDs stable when only labels or colors change.

## Example

The tables below show an example of a 3x3 Risk Matrix. In Excel, each `grid` heading is a separate column. The colors in the cells illustrate cell fills.

### `matrix_meta`

| Property | Value |
| --- | --- |
| `type` | `risk_matrix` |
| `urn` | `urn:intuitem:risk:matrix:sample-matrix.1` |
| `ref_id` | `SAMPLE-MATRIX.1` |
| `name` | Sample risk matrix |
| `description` | Probability and impact combined into a risk level |

### `matrix_content`

| type | id | color | abbreviation | name | description | grid | grid | grid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `probability` | `0` | <mark style="background-color:green;">&#xA0;&#xA0;&#xA0;&#xA0;</mark> | L | Unlikely | Not expected often | `0` | `0` | `1` |
| `probability` | `1` | <mark style="background-color:orange;">&#xA0;&#xA0;&#xA0;&#xA0;</mark> | M | Possible | Could happen | `0` | `1` | `2` |
| `probability` | `2` | <mark style="background-color:red;">&#xA0;&#xA0;&#xA0;&#xA0;</mark> | H | Likely | Expected often | `1` | `2` | `2` |
| `impact` | `0` | <mark style="background-color:green;">&#xA0;&#xA0;&#xA0;&#xA0;</mark> | L | Minor | Limited consequences |  |  |  |
| `impact` | `1` | <mark style="background-color:orange;">&#xA0;&#xA0;&#xA0;&#xA0;</mark> | M | Moderate | Noticeable consequences |  |  |  |
| `impact` | `2` | <mark style="background-color:red;">&#xA0;&#xA0;&#xA0;&#xA0;</mark> | H | Major | Serious consequences |  |  |  |
| `risk` | `0` | <mark style="background-color:green;">&#xA0;&#xA0;&#xA0;&#xA0;</mark> | L | Low | Limited risk |  |  |  |
| `risk` | `1` | <mark style="background-color:orange;">&#xA0;&#xA0;&#xA0;&#xA0;</mark> | M | Medium | Moderate risk |  |  |  |
| `risk` | `2` | <mark style="background-color:red;">&#xA0;&#xA0;&#xA0;&#xA0;</mark> | H | High | Significant risk |  |  |  |

To see an example of a Risk Matrix in a complete Excel file, download [`risk-matrix-3x3-mult.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/excel/matrix/risk-matrix-3x3-mult.xlsx) and open its `3x3-mult_meta` and `3x3-mult_content` sheets.

## Advanced: YAML representation of this object

This section is mainly for advanced users and debugging. The excerpt below shows how the Risk Matrix from the tables above can appear in the converted YAML.

<details>
<summary>Show YAML</summary>

```yaml
objects:
  risk_matrix:
  - urn: urn:intuitem:risk:matrix:sample-matrix.1
    ref_id: SAMPLE-MATRIX.1
    name: Sample risk matrix
    description: Probability and impact combined into a risk level
    probability:
    - id: 0
      abbreviation: L
      name: Unlikely
      description: Not expected often
      hexcolor: "#008000"
    - id: 1
      abbreviation: M
      name: Possible
      description: Could happen
      hexcolor: "#FFA500"
    - id: 2
      abbreviation: H
      name: Likely
      description: Expected often
      hexcolor: "#FF0000"
    impact:
    - id: 0
      abbreviation: L
      name: Minor
      description: Limited consequences
      hexcolor: "#008000"
    - id: 1
      abbreviation: M
      name: Moderate
      description: Noticeable consequences
      hexcolor: "#FFA500"
    - id: 2
      abbreviation: H
      name: Major
      description: Serious consequences
      hexcolor: "#FF0000"
    risk:
    - id: 0
      abbreviation: L
      name: Low
      description: Limited risk
      hexcolor: "#008000"
    - id: 1
      abbreviation: M
      name: Medium
      description: Moderate risk
      hexcolor: "#FFA500"
    - id: 2
      abbreviation: H
      name: High
      description: Significant risk
      hexcolor: "#FF0000"
    grid:
    - - 0
      - 0
      - 1
    - - 0
      - 1
      - 2
    - - 1
      - 2
      - 2
```

</details>

## Related pages

- [Library objects](README.md)
- [Excel examples](../examples.md)
- [Translate library content](../translations.md)
- [Create a library with Excel](../create-library-with-excel.md)
- [Import a library](../import-library.md)
- [Update a library](../update-library.md)
