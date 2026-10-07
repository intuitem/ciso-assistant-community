---
description: Understand libraries and choose the right path to create, import, test, and maintain them
---

# Libraries

Libraries package reusable governance content for CISO Assistant. A library can contain a framework, a threat catalogue, reference controls, a risk matrix, mappings, and many other object types.

{% hint style="info" %}
**New to libraries?** Explore the [Library objects](library-objects/README.md), then create your first library directly in CISO Assistant with the [Library builder](../authoring/library-builder.md). You can also follow [Create a Library](create-library.md) if you prefer working with a spreadsheet.
{% endhint %}

## What is a library?

A library is a portable package of objects. It gives those objects a stable identity, a version, and a format that CISO Assistant can import.

One library may contain only one object, such as an internal framework. It can also bundle several related objects, such as a framework together with its reference controls and threats.

You can create a library directly in the [Library builder](../authoring/library-builder.md). The library is stored on the CISO Assistant instance where you create it. Outside the instance, libraries use two file formats: **Excel** *(.xlsx)* and **YAML** *(.yaml)*. Excel is the human-editable source format. YAML is the format CISO Assistant reads. When you import an Excel workbook through the Library catalog, CISO Assistant converts it to YAML automatically.

You normally do not edit YAML directly, including when updating a library. Instead, update the Excel workbook or edit the library in the Library builder.

## What can a library contain?

The following pages describe each object separately. Not every object is needed for every library.

| Element | What it is for |
| --- | --- |
| [Library metadata](library-objects/library-metadata.md) | Required properties that identify and describe the library itself. |
| [Framework](library-objects/framework.md) | A tree of sections and requirements used to run audits. |
| [Implementation groups](library-objects/implementation-groups.md) | Optional groups that select a relevant subset of framework requirements. |
| [Answers](library-objects/answers.md) | Reusable answer sets used by questions defined in framework requirements. |
| [Scores](library-objects/scores.md) | The labels and meanings associated with a scoring scale. |
| [Threats](library-objects/threats.md) | A reusable catalogue of events or situations that can cause harm. |
| [Reference controls](library-objects/reference-controls.md) | Reusable control templates that can support requirements or mitigate threats. |
| [URN prefixes](library-objects/urn-prefixes.md) | Technical prefixes used when you need to link external/internal threats/reference controls to requirements of a framework |
| [Risk matrices](library-objects/risk-matrices.md) | The probability, impact, and risk-level model used in risk assessments. |
| [Mappings](library-objects/mappings.md) | Links between the requirements of two frameworks. |

Every Excel version of a library must include a `library_meta` sheet, which defines the properties of the library as a whole. See [Library metadata](library-objects/library-metadata.md) for more details.

For an overview of how these elements relate to one another, see [Library objects](library-objects/README.md).

## Why use libraries?

Libraries keep content reusable and consistent. Instead of rebuilding the same framework for every audit or project, you can import it once and use it wherever it is needed.

They also make change manageable. A library version records the content that was published, while stable identifiers let CISO Assistant recognise the same objects when you publish a later version.

## Choose your path

Not sure where to start? Use the table below to find the page that matches your goal.

| If you want to... | Start here |
| --- | --- |
| Create your first framework from an Excel file | [Create a Library](create-library.md) |
| Follow a complete small example | [Guided example: create your first framework](guided-example.md) |
| Browse the available sample workbooks | [Examples](examples.md) |
| Import a finished library into CISO Assistant | [Import a library](import-library.md) |
| Publish a new version of a custom library | [Update a library](update-library.md) |
| Handle a standard with its own import workflow | [Special cases](special-cases/README.md) |

## Related concepts

- [Libraries concept](../../concepts/libraries.md)
- [Frameworks concept](../../concepts/frameworks.md)
- [Vocabulary](../../introduction/vocabulary.md)
