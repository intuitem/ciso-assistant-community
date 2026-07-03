---
description: Manage reusable document templates and bulk-import them from a zip
---

# Document templates

A **document template** is a reusable Markdown body that seeds a new document. When you create an authored document, the editor's template picker offers the templates matching that document's **type** and **language**, so authors start from a consistent baseline instead of a blank page.

Templates live on the **Document templates** page.

## Built-in vs. custom templates

- **Built-in templates** ship with the platform (a library of common security policies) and are **read-only** — you can preview them but not edit or delete them.
- **Custom templates** are yours: created in-app or bulk-imported. They can be edited, deleted, and are scoped to the domain you create them in (built-in templates are visible everywhere).

Opening any template shows a **rendered preview** of its content; the built-in badge marks the ones that ship with the platform.

## Create a template

Choose **Add document template** and set its reference, name, **Document type**, and language. The body is written on the template's edit page in the same Markdown editor (toolbar + preview) used for documents — kept off the creation dialog so long content is authored where there's room for it.

## Bulk-import templates from a zip

**Import templates** uploads a `.zip` of Markdown files and creates one custom template per file. The zip mirrors the built-in library layout:

```text
templates.zip
├── en/
│   ├── access_control.md
│   └── incident_response.md
└── fr/
    └── access_control.md
```

- The **immediate parent folder is the language** (`en/…`, `fr/…`).
- The **filename becomes the reference** (`access_control.md` → `access_control`).
- Optional YAML **frontmatter** sets the title, description, and type:

```yaml
---
title: Access Control Policy
description: How access to systems is granted and reviewed
document_type: procedure
---
```

`document_type` is validated against the built-in types and defaults to `policy`; the rest of the file is the template body. Re-importing the same reference and language **updates** the existing custom template rather than duplicating it.

{% hint style="info" %}
Imports are bounded for safety: up to **1000 files**, **10 MB** per file, **50 MB** total. Files that aren't `.md`, that sit outside a language folder, or that collide with a **built-in** template are skipped and listed in the import summary.
{% endhint %}

## Related

- [Authoring documents](authoring-documents.md)
- [Documents](../../concepts/documents.md)
