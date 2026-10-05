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

An asterisk (<mark style="color:$danger;">*</mark>) marks a required field. <mark style="color:$info;">T</mark> marks a field that supports translations.

### `<object>_meta`

The metadata sheet is a key-value table with one property per row.

| Property | Meaning | Format / allowed values |
| --- | --- | --- |
| `type`<mark style="color:$danger;">*</mark> | Identifies the object type | Enter `risk_matrix` |
| `urn`<mark style="color:$danger;">*</mark> | Unique identifier of the matrix | `urn:<packager>:risk:matrix:<identifier>` |
| `ref_id`<mark style="color:$danger;">*</mark> | Short identifier of the matrix | Letters, numbers, `.`, `_`, or `-` only; no spaces. Keep it stable across versions |
| `name`<mark style="color:$danger;">*</mark> <mark style="color:$info;">T</mark> | Name shown to users | Text |
| `description`<mark style="color:$danger;">*</mark> <mark style="color:$info;">T</mark> | What the matrix measures | Text |

### `<object>_content`

The content sheet contains one row per probability, impact, or risk level. Add one `grid` column per impact level; fill those columns on probability rows with the resulting risk level IDs.

| Field | Meaning | Format / allowed values |
| --- | --- | --- |
| `type`<mark style="color:$danger;">*</mark> | Kind of level defined by the row | `probability`, `impact`, or `risk` |
| `id`<mark style="color:$danger;">*</mark> | Numeric identifier of the level within its type | Whole number |
| `color`<mark style="color:$danger;">*</mark> | Color shown for this level | Required column; set the Excel cell's fill color if needed. The cell text can stay empty |
| `abbreviation`<mark style="color:$danger;">*</mark> <mark style="color:$info;">T</mark> | Short label for the level | Text |
| `name`<mark style="color:$danger;">*</mark> <mark style="color:$info;">T</mark> | Name of the level | Text |
| `description`<mark style="color:$danger;">*</mark> <mark style="color:$info;">T</mark> | Explanation of the level | Text |
| `grid`<mark style="color:$danger;">*</mark> | Risk level for one probability and impact combination | On probability rows, a `risk` level `id`. Repeat the `grid` column once per impact level |

The first `grid` column corresponds to the lowest impact ID, the next to the next impact ID, and so on. The converter orders probabilities and impacts by their IDs.

See [Translate library content](../translations.md) for how to add translations.

## Relationships with other objects

A Risk Matrix is an independent library object. It does not need a [Framework](framework.md) sheet in the same workbook. Once imported, users can select it when evaluating risks.

## Tips

### When creating a library

- List the probability and impact IDs before filling the grid, so every intersection points to a defined risk ID
- Set colors through the Excel cell fills, not by typing a color code into the `color` column

### When updating a library

- Keep the matrix `urn` and existing level IDs stable when only labels or colors change
- Check every grid cell if you add, remove, or reorder a probability, impact, or risk level

## Example

The tables below show an example of a two-by-two Risk Matrix. In Excel, each `grid` heading is a separate column, and the `color` cells can have fill colors even though their values are empty.

### `matrix_meta`

| Property | Value |
| --- | --- |
| `type` | `risk_matrix` |
| `urn` | `urn:intuitem:risk:matrix:sample-matrix.1` |
| `ref_id` | `SAMPLE-MATRIX.1` |
| `name` | Sample risk matrix |
| `description` | Probability and impact combined into a risk level |

### `matrix_content`

| `type` | `id` | `color` | `abbreviation` | `name` | `description` | `grid` | `grid` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `probability` | `0` |  | L | Unlikely | Not expected often | `0` | `1` |
| `probability` | `1` |  | H | Likely | Expected often | `1` | `2` |
| `impact` | `0` |  | L | Minor | Limited consequences |  |  |
| `impact` | `1` |  | H | Major | Serious consequences |  |  |
| `risk` | `0` |  | L | Low | Limited risk |  |  |
| `risk` | `1` |  | M | Medium | Moderate risk |  |  |
| `risk` | `2` |  | H | High | Significant risk |  |  |

To see an example of a Risk Matrix in a complete Excel file, download [`risk-matrix-3x3-mult.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/excel/matrix/risk-matrix-3x3-mult.xlsx) and open its `3x3-mult_meta` and `3x3-mult_content` sheets.

## Advanced: YAML representation of this object

This section is mainly for advanced users and debugging. The excerpt below shows how the Risk Matrix from the tables above can appear after import.

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
    - id: 1
      abbreviation: H
      name: Likely
      description: Expected often
    impact:
    - id: 0
      abbreviation: L
      name: Minor
      description: Limited consequences
    - id: 1
      abbreviation: H
      name: Major
      description: Serious consequences
    risk:
    - id: 0
      abbreviation: L
      name: Low
      description: Limited risk
    # ...
    grid:
    - - 0
      - 1
    - - 1
      - 2
```

The first `grid` row corresponds to probability `0`; its values correspond to impacts `0` and `1`.
</details>

## Related pages

- [Library objects](README.md)
- [Excel examples](../examples.md)
- [Translate library content](../translations.md)
- [Create a library with Excel](../create-library-with-excel.md)
- [Import a library](../import-library.md)
- [Update a library](../update-library.md)
