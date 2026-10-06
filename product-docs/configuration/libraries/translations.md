---
description: Learn how to add translations to library content
---

# Translate library content

You can add translations to a library by adding translated keys and columns to its Excel sheets. This works for any field that supports translations, regardless of the object type.

## Principle

Keep the original field for the library's primary language, which is defined in `library_meta` as `locale`. For each field marked (<mark style="color:$info;">T</mark>) in an object's documentation, create an additional key or column using the same name followed immediately by the language code in square brackets (for example, keep `name` and add `name[fr]` for French). The locale code must comply with [ISO 639 Set 1](https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes#Table) (e.g., `en` or `fr`).

In a `_meta` sheet, add a new key and its translated value on a separate row. In a `_content` sheet, add a new column and fill it for the rows you want to translate.

{% hint style="warning" %}
Only fields marked (<mark style="color:$info;">T</mark>) support translations. If you translate a key or column that does not support translations, CISO Assistant will not display the translated value, even if you add it manually to the final YAML.
{% endhint %}

## Example

This example adds French translations to the example Framework shown on the [Framework](library-objects/framework.md#example) page. Only the fields relevant to translation are shown.

### `fwk_meta`

| Property | Value |
| --- | --- |
| `name` | Sample framework |
| `description` | A short set of access management requirements |
| `name[fr]` | Exemple de framework |
| `description[fr]` | Un court ensemble d'exigences sur la gestion des accès |

### `fwk_content`

| ref_id | name | description | name[fr] | description[fr] |
| --- | --- | --- | --- | --- |
| `ACCESS` | Access management |  | Gestion des accès |  |
| `ACCESS.1` | Review access rights | Review user access regularly | Revoir les droits d'accès | Revoir régulièrement les droits d'accès des utilisateurs |
