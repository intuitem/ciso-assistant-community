---
description: Understand reusable answer sets for framework questions
---

# Answers

Questions are written in a [Framework](framework.md). An Answers object defines the type and reusable choices those questions use, such as a single choice, multiple choices, free text, or a date.

## Excel structure and fields

An Answers object uses two sheets:
* `<object>_meta` describes the object.
* `<object>_content` lists the answer sets.

For example, if `answ` is the object prefix, the sheets are `answ_meta` and `answ_content`.

An asterisk (<mark style="color:$danger;">*</mark>) marks a required field. <mark style="color:$info;">T</mark> marks a field that supports translations.

### `<object>_meta`

The metadata sheet is a key-value table with one property per row.

| Property | Meaning | Format / allowed values |
| --- | --- | --- |
| `type`<mark style="color:$danger;">*</mark> | Identifies the object type | Enter `answers` |
| `name`<mark style="color:$danger;">*</mark> | Defines the object prefix used to name its sheet pair and link it to a framework | The sheet name prefix (e.g., `answ`). Do not include `_meta` or `_content`. |

For example, if `name` is `answ`, the object is defined by `answ_meta` and `answ_content`. You will need to set the framework's `answers_definition` property to the same prefix.

### `<object>_content`

The content sheet contains one row per answer set. For choice questions, put one choice per line in the `question_choices` cell. Use the same line order in columns that describe each choice; enter `/` for a choice that has no value in an optional column.

| Field | Meaning | Format / allowed values |
| --- | --- | --- |
| `id`<mark style="color:$danger;">*</mark> | Identifier used by questions in the framework | Unique text identifier within this sheet |
| `question_type`<mark style="color:$danger;">*</mark> | How the user answers | `unique_choice`, `multiple_choice`, `text`, or `date` |
| `question_choices` <mark style="color:$info;">T</mark> | Choices offered for a choice question | One choice per line; required for `unique_choice` and `multiple_choice`. Start a continuation line with a vertical bar to keep a line break inside one choice |
| `description` <mark style="color:$info;">T</mark> | Explanation for each choice | One value per choice, on separate lines; `/` for none |
| `select_implementation_groups` | Groups selected when a choice is chosen | Group `ref_id` values separated by commas within a choice; one line per choice, `/` for none |
| `add_score` | Points contributed by each choice | Whole number, zero or greater, per choice; one line per choice |
| `compute_result` | Compliance result contributed by each choice | `compliant`, `partially_compliant`, `non_compliant`, or `not_applicable`; one line per choice, `/` for none |
| `color` | Color shown for each choice | `#RRGGBB` per choice, one line per choice, `/` for none |

The `question_choices` cell can be empty for `text` and `date`. See [Translate library content](../translations.md) for how to add translations.

{% hint style="info" %}
Use `select_implementation_groups` only for a questionnaire that reveals additional requirements based on an answer. It selects groups defined in [Implementation Groups](implementation-groups.md).
{% endhint %}

## Relationships with other objects

Set `answers_definition` in the [Framework](framework.md) metadata sheet to the Answers object prefix. In the framework content, `questions` contains the question text and `answer` contains an `id` from this sheet. One answer ID can be used for every question in a requirement, or each question can have its own ID on a separate line.

Answer choices can select [Implementation Groups](implementation-groups.md) or add points to the framework's [Scores](scores.md). Their `compute_result` values can also contribute to a requirement's compliance result.

## Tips

### When creating a library

- Reuse an answer `id` when several questions have the same type and choices
- Keep choice lines aligned across `question_choices` and any per-choice columns you use

### When updating a library

- Keep existing answer IDs and choice order stable when possible; choice URNs use their position in the list
- Review questions that reuse an answer set before changing its choices or scoring

## Example

The tables below show an example of an Answers object for a single-choice question.

### `answ_meta`

| Property | Value |
| --- | --- |
| `type` | `answers` |
| `name` | `answ` |

### `answ_content`

| `id` | `question_type` | `question_choices` |
| --- | --- | --- |
| `yes_no` | `unique_choice` | Yes<br>No |

In Excel, `Yes` and `No` occupy separate lines in the same cell. To see an example of Answers in a complete Excel file, download [`example_framework.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/example_framework.xlsx) or [`example_questionnaire.xlsx`](https://github.com/intuitem/ciso-assistant-community/raw/refs/heads/main/tools/example_questionnaire.xlsx) and open their `answ_meta` and `answ_content` sheets.

## Advanced: YAML representation of this object

This section is mainly for advanced users and debugging. The excerpt below shows how the Answers from the tables above can appear inside a [Framework](framework.md) after import.

<details>
<summary>Show YAML</summary>

```yaml
objects:
  framework:
    urn: urn:intuitem:risk:framework:sample-framework.1
    # ...
    requirement_nodes:
    - urn: urn:intuitem:risk:req_node:sample-framework.1:access.1
      assessable: true
      depth: 1
      ref_id: ACCESS.1
      # ...
      questions:
        urn:intuitem:risk:req_node:sample-framework.1:access.1:question:1:
          type: unique_choice
          text: Are administrator accounts reviewed?
          choices:
          - urn: urn:intuitem:risk:req_node:sample-framework.1:access.1:question:1:choice:1
            value: 'Yes'
          - urn: urn:intuitem:risk:req_node:sample-framework.1:access.1:question:1:choice:2
            value: 'No'
```

The question text comes from `fwk_content`. Its type and choices come from `answ_content`.
</details>

## Related pages

- [Library objects](README.md)
- [Framework](framework.md)
- [Implementation Groups](implementation-groups.md)
- [Scores](scores.md)
- [Excel examples](../examples.md)
- [Translate library content](../translations.md)
- [Create a library with Excel](../create-library-with-excel.md)
- [Import a library](../import-library.md)
- [Update a library](../update-library.md)
