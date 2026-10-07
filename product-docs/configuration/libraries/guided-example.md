---
description: Build a first Framework from a short fictional standard
---

# Guided example: create your first framework

We will use the two-page [Octopus Habitat Security Standard (OHSS)](../../.gitbook/assets/octopus-habitat-security-standard-en.pdf) as our source. In this fictional standard, an octopus must secure a permanently submerged home to meet the Mermaid Authority's certification criteria. Read the PDF before continuing: we will turn its content into a CISO Assistant Framework.

{% hint style="info" %}
This walkthrough mainly shows how to create the library in Excel. If you prefer the [Library builder](../authoring/library-builder.md), you can follow the same reasoning to organize the standard. Only the way you enter the content changes.
{% endhint %}

## Before you begin

First, look at how the standard is organized. You do not need to decide on every Excel sheet yet. Identify:

- The three sections and their numbered requirements. These form the main structure of the Framework.
- The assessment questions included in requirements `OH 2.2` and `OH 3.2`, and the score scale at the end of the document.
- The review themes used to filter requirements. They are optional: a requirement can have several themes or none.

We will use these observations to decide what to create in the library, then build it one part at a time.

## Start small, then build up

For this example, we assume that the workbook already contains `library_meta`, `framework_meta`, and `framework_content`. We will fill the metadata sheets first, then outline the Framework's sections and requirements.

{% hint style="info" %}
You can generate these sheets already filled with `prepare_framework_v2.py`. Enter the shared values in the `base` sheet of its configuration workbook, with `octopus-habitat-security-standard` as `urn_root` to obtain the URNs below. [Create a Library](create-library.md#generate-a-framework-workbook) explains how to run the script.
{% endhint %}

Both metadata sheets use one property per row, with its name in column A and its value in column B. The table headers below are only here to make the examples easier to read.

### Fill `library_meta`

This sheet identifies the library that will contain our Framework. For this example, intuitem provides and packages the fictional content.

| Property | Value |
| --- | --- |
| `type` | `library` |
| `urn` | `urn:intuitem:risk:library:octopus-habitat-security-standard` |
| `version` | `1` |
| `locale` | `en` |
| `ref_id` | `OHSS.v1` |
| `name` | Octopus Habitat Security Standard |
| `description` | Safeguards for an octopus-managed home permanently submerged beneath the reef. |
| `copyright` | © 2026 intuitem |
| `provider` | intuitem |
| `packager` | intuitem |

Here is how we chose the values:

- `name` is the title on the PDF. `description` summarizes its opening paragraph, and `locale` is `en` because the source is in English.
- `ref_id` combines the standard's acronym, `OHSS`, with `v1` to identify this edition.
- `urn` follows `urn:<packager>:risk:library:<identifier>`. Here, `intuitem` is the packager, `library` identifies the object type, and the final part is a lowercase identifier based on the title. It has no version suffix, so the same URN can identify later updates to this library.
- For this example, intuitem provides and packages the library. The Mermaid Authority is the fictional certifying body in the PDF.

{% hint style="warning" %}
The `v1` in `ref_id` marks this edition of the standard, while `library_meta.version` tracks updates to the library. For a correction or minor addition, keep the library and Framework URNs and the identifiers of existing requirements, then increase `library_meta.version` from `1` to `2`. If a new edition substantially changes the Framework's structure or requirements, create a separate library with a distinct URN and new Framework and requirement URNs. Replacing the existing structure under the same identifiers can break existing audits.
{% endhint %}

See [Library metadata](library-objects/library-metadata.md) for what each property means.

### Fill `framework_meta`

For a library built around one Framework, `ref_id`, `name`, and `description` are generally the same in both metadata sheets. We keep them identical here. The `type` and `urn` differ because they identify two different objects. The Framework also needs a `base_urn` for its sections and requirements.

| Property | Value |
| --- | --- |
| `type` | `framework` |
| `urn` | `urn:intuitem:risk:framework:octopus-habitat-security-standard` |
| `base_urn` | `urn:intuitem:risk:req_node:octopus-habitat-security-standard` |
| `ref_id` | `OHSS.v1` |
| `name` | Octopus Habitat Security Standard |
| `description` | Safeguards for an octopus-managed home permanently submerged beneath the reef. |

We will add links to other objects here when we introduce them. For the full list of fields, see [Framework](library-objects/framework.md).

### Sketch `framework_content`

Begin with the standard's sections and requirements, in the same order as the PDF. A section is a heading at `depth` `1`, so leave `assessable` empty. Each requirement beneath it goes at `depth` `2` and gets an `x` in `assessable`. Apart from these two columns, fill only `ref_id`, `name`, and `description` for now.

Here is how to start the `framework_content` sheet with the first section:

| assessable | depth | ref_id | name | description |
| --- | --- | --- | --- | --- |
|  | `1` | `OH.1` | Access and identity |  |
| `x` | `2` | `OH.1.1` |  | Maintain an inventory of permanent residents and authorized visitors, including the areas each may enter. |
| `x` | `2` | `OH.1.2` |  | Use a controlled entry procedure for visitors. Record the host, entry and exit times, and review the log at least monthly. |

The PDF uses identifiers such as `OH 1.1`. Because `ref_id` cannot contain spaces, we use `OH.1.1` in the workbook and follow the same pattern for the other rows. We also assign `OH.1` to the first section. Continue with `OH.1.3`, then add sections 2 and 3 with their requirements. Leave the questions, review themes, and score scale for later: the goal here is to establish the Framework's hierarchy before adding more objects.

[TO BE CONTINUED]
