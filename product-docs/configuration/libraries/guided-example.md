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

For this example, we assume that the workbook already contains `library_meta`, `fwk_meta`, and `fwk_content`. We will fill the metadata sheets first, then outline the Framework's sections and requirements.

{% hint style="info" %}
To generate these sheets already filled, use the `prepare_framework_v2_config.xlsx` Excel workbook with `prepare_framework_v2.py`. Open the collapsed section below to see what to enter in its `base` sheet, then [run the script as explained here](create-library.md#generate-a-framework-workbook).

<details>
<summary>Show the values to enter in the configuration workbook</summary>

In the `base` sheet of `prepare_framework_v2_config.xlsx`, replace the example values with these ones:

| Property | Value | Why this value? |
| --- | --- | --- |
| `urn_root` | `octopus-habitat-security-standard` | A stable identifier for this standard, without a version number, so minor updates can keep the same URNs. |
| `locale` | `en` | The source standard is in English. |
| `ref_id` | `OHSS.v1` | The standard's abbreviation and edition, useful for readers without making it part of the URNs. |
| `framework_name` | Octopus Habitat Security Standard | The title used in the source document. |
| `description` | The Octopus Habitat Security Standard (OHSS) sets baseline safeguards for an octopus-managed home that remains submerged beneath the reef. To qualify for certification by the Mermaid Authority, the owner must show that access is controlled, essential habitat systems remain safe, and incidents can be handled. | The opening two sentences of the standard describe its scope. A shorter summary would also be fine. |
| `copyright` | © 2026 intuitem | The attribution chosen for this example. |
| `provider` | Mermaid Authority | The fictional authority behind the standard and its certification criteria. |
| `packager` | `intuitem` | The organization preparing the library for CISO Assistant. |
| `framework_sheet_base_name` | `fwk` | This produces the `fwk_meta` and `fwk_content` sheets used below. |

Leave the optional entries beginning with `#` disabled for now. We will add other objects only when we need them. The script uses these shared values to fill both metadata sheets.

</details>
{% endhint %}

## Fill in the metadata

We start with the metadata because it is usually quick to fill in. It also establishes the library's identity and the Framework's identifiers before we add content, helping us keep those values consistent later.

Both metadata sheets use one property per row, with its name in column A and its value in column B. The table headers below are only here to make the examples easier to read.

### Fill `library_meta`

This sheet identifies the library that will contain our Framework. For this example, the Mermaid Authority provides the standard, while intuitem packages it for CISO Assistant.

| Property | Value |
| --- | --- |
| `type` | `library` |
| `urn` | `urn:intuitem:risk:library:octopus-habitat-security-standard` |
| `version` | `1` |
| `locale` | `en` |
| `ref_id` | `OHSS.v1` |
| `name` | Octopus Habitat Security Standard |
| `description` | The Octopus Habitat Security Standard (OHSS) sets baseline safeguards for an octopus-managed home that remains submerged beneath the reef. To qualify for certification by the Mermaid Authority, the owner must show that access is controlled, essential habitat systems remain safe, and incidents can be handled. |
| `copyright` | © 2026 intuitem |
| `provider` | Mermaid Authority |
| `packager` | intuitem |

Here is how we chose the values:

- `name` is the title on the PDF. We copied the opening two sentences into `description`, though a shorter summary would also work. `locale` is `en` because the source is in English.
- `ref_id` combines the standard's acronym, `OHSS`, with `v1` to identify this edition.
- `urn` follows `urn:<packager>:risk:library:<identifier>`. Here, `intuitem` is the packager, `library` identifies the object type, and the final part is a lowercase identifier based on the title. It has no version suffix, so the same URN can identify later updates to this library.

{% hint style="warning" %}
The `v1` in `ref_id` marks this edition of the standard, while `library_meta.version` tracks updates to the library. For a correction or minor addition, keep the library and Framework URNs and the identifiers of existing requirements, then increase `library_meta.version` from `1` to `2`. If a new edition substantially changes the Framework's structure or requirements, create a separate library with a distinct URN and new Framework and requirement URNs. Replacing the existing structure under the same identifiers can break existing audits.
{% endhint %}

See [Library metadata](library-objects/library-metadata.md) for what each property means.

### Fill `fwk_meta`

For a library built around one Framework, `ref_id`, `name`, and `description` are generally the same in both metadata sheets. We keep them identical here. The `type` and `urn` differ because they identify two different objects. The Framework also needs a `base_urn` for its sections and requirements.

| Property | Value |
| --- | --- |
| `type` | `framework` |
| `urn` | `urn:intuitem:risk:framework:octopus-habitat-security-standard` |
| `base_urn` | `urn:intuitem:risk:req_node:octopus-habitat-security-standard` |
| `ref_id` | `OHSS.v1` |
| `name` | Octopus Habitat Security Standard |
| `description` | The Octopus Habitat Security Standard (OHSS) sets baseline safeguards for an octopus-managed home that remains submerged beneath the reef. To qualify for certification by the Mermaid Authority, the owner must show that access is controlled, essential habitat systems remain safe, and incidents can be handled. |

We will add links to other objects here when we introduce them. For the full list of fields, see [Framework](library-objects/framework.md).

## Plan the Framework structure

Before filling `fwk_content`, make a simple outline of the standard. The sheet will have one row per section or requirement, in the same order as the source document.
The `depth` column expresses the hierarchy. Often, `1` marks a main section, `2` its requirements, and `3` their subrequirements, but the meaning of each level depends on the source Framework. In `assessable`, leave headings empty and enter `x` for requirements users will assess. Use `name` for a short title and `description` for the full requirement text. See [Framework](library-objects/framework.md) for the fields in this sheet.

For OHSS, identify the three main sections, then list the numbered requirements beneath each one. Decide which rows are headings and which are assessable before copying the text into Excel. Keep the source identifiers at hand: they will help us choose stable `ref_id` values.

This planning step matters. If the hierarchy turns out to be wrong after you have added questions, themes, and scores, you may need to reorganize much of the workbook. It is harder to change once the Framework is used in audits.

{% hint style="info" %}
Some Frameworks can have sections or requirements without an identifier. In that case, leave `ref_id` empty for those rows and fill in `name`, `description`, or both.
{% endhint %}

## Add the first section to `fwk_content`

Start with **Access and identity**. Add its heading at `depth` `1` with an empty `assessable` cell, then add its requirements at `depth` `2` with `x` in `assessable`. For now, fill only `ref_id`, `name`, and `description` alongside these two columns.

Here is the first section in `fwk_content`:

| assessable | depth | ref_id | name | description |
| --- | --- | --- | --- | --- |
|  | `1` | `OH.1` | Access and identity |  |
| `x` | `2` | `OH.1.1` |  | Maintain an inventory of permanent residents and authorized visitors, including the areas each may enter. |
| `x` | `2` | `OH.1.2` |  | Use a controlled entry procedure for visitors. Record the host, entry and exit times, and review the log at least monthly. |
| `x` | `2` | `OH.1.3` |  | Revoke access within one tide cycle when a resident or contractor no longer needs it. |

The PDF uses identifiers such as `OH 1.1`. As a best practice, we avoid spaces in `ref_id`, so we write `OH.1.1` in the workbook and follow the same pattern for the other rows. We also assign `OH.1` to the first section so it is easy to identify in CISO Assistant and its requirements are easier to locate.

If you are still unsure about the outline, you can enter just the three main section headings in Excel first and check whether the structure makes sense. Then add their requirements. Leave the questions, review themes, and score scale for later. The goal here is to establish the Framework's hierarchy before adding more objects.

## Add the second section to `fwk_content`

Continue in the same sheet with **Habitat and equipment**. Its heading is at `depth` `1`, just like the first section.

This time, `OH 2.1` has two subrequirements: put the parent at `depth` `2` and its children at `depth` `3`. Here, `OH 2.1` serves as a section heading. Its source wording goes in `name`, `description` stays empty, and it is not assessable. Its two specific children receive `x`, so we assess them without assessing the parent again. The following requirements, `OH 2.2` and `OH 2.3`, return to `depth` `2` because they are not children of `OH 2.1`.

| assessable | depth | ref_id | name | description |
| --- | --- | --- | --- | --- |
|  | `1` | `OH.2` | Habitat and equipment |  |
|  | `2` | `OH.2.1` | Inspect and maintain habitat structures and access points. |  |
| `x` | `3` | `OH.2.1.1` |  | Inspect structural supports, anchoring points and entry hatches at least quarterly. |
| `x` | `3` | `OH.2.1.2` |  | Record and repair defects that could destabilize the habitat or permit unauthorized entry. |
| `x` | `2` | `OH.2.2` |  | Equip the habitat with alerts for strong currents and unauthorized entry, and test both alerts at least monthly. |
| `x` | `2` | `OH.2.3` |  | Keep a tested backup power source for critical lighting, alerts and communication equipment. |

The source also includes assessment questions under `OH 2.2`. We keep only the requirement text for now and will return to its questions and answers after the hierarchy is in place.

{% hint style="info" %}
If you want a reminder, you can add the `questions` column now and put a temporary `x` in the `OH.2.2` row.
{% endhint %}

## Add the third section to `fwk_content`

The final section, **Monitoring and response**, follows the simpler pattern we used for the first one: one heading at `depth` `1`, followed by three assessable requirements at `depth` `2`.

| assessable | depth | ref_id | name | description |
| --- | --- | --- | --- | --- |
|  | `1` | `OH.3` | Monitoring and response |  |
| `x` | `2` | `OH.3.1` |  | Maintain an emergency contact route and a safe evacuation path from each occupied chamber. |
| `x` | `2` | `OH.3.2` |  | Record security and safety incidents, including the time, affected area, actions taken and outcome. |
| `x` | `2` | `OH.3.3` |  | Review every incident within seven days and track corrective actions to closure. |

The question attached to `OH 3.2` can be added later, alongside the other questions. For now, keep the requirements and their hierarchy in place.

[TO BE CONTINUED]
