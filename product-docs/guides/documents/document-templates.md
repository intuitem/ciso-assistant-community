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

Choose **Add document template** and set its reference, name, **Document type**, language, and optionally a **Provider** (a free-text attribution such as `CIS` or `NIST`). The body is written on the template's edit page in the same Markdown editor (toolbar + preview) used for documents — kept off the creation dialog so long content is authored where there's room for it.

{% hint style="info" %}
For a single template it's quicker to create it directly here than to build a one-file zip.
{% endhint %}

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

- The **immediate parent folder is the language** (`en/…`, `fr/…`) — or, for a flat file at the archive root, a `locale:` frontmatter key.
- The **filename becomes the reference** (`access_control.md` → `access_control`).
- Optional YAML **frontmatter** sets the template's metadata:

```yaml
---
title: Access Control Policy
description: How access to systems is granted and reviewed
document_type: procedure
locale: en
provider: CIS
---
```

Every frontmatter key is optional:

- **title** — defaults to the title-cased filename.
- **description** — free text.
- **document_type** — validated against the built-in types; defaults to `policy`.
- **locale** — the language fallback when the file isn't inside a language folder (handy for a flat, single-file bundle). A `<locale>/` folder always wins over this.
- **provider** — free-text attribution (e.g. `CIS`, `NIST`), shown and filterable on the templates page.

The rest of the file is the template body. Re-importing the same reference and language **updates** the existing custom template rather than duplicating it. Imported templates are always **custom** (never built-in).

{% hint style="info" %}
Imports are bounded for safety: up to **1000 files**, **10 MB** per file, **50 MB** total. Files that aren't `.md`, that carry no language (neither a `<locale>/` folder nor a `locale:` frontmatter), or that collide with a **built-in** template are skipped and listed in the import summary.
{% endhint %}

## Browse and clean up

The **Document templates** page lists every template with a **Provider** column, and filters by **Document type**, **Language**, **Built-in**, and **Domain**, plus a text search. To remove templates in bulk — for example after a bad import — select the rows and use the batch **Delete** action; built-in templates in the selection are protected and left untouched.

When you author a document, the editor's template picker shows a **search box** once there are enough templates to warrant it, filtering by title, description, and provider.

## Related

- [Authoring documents](authoring-documents.md)
- [Documents](../../concepts/documents.md)
