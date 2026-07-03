---
description: Create, write, review, and publish a document in CISO Assistant
---

# Authoring documents

This walkthrough covers writing a document in-platform — from a blank page or a template — and taking it through review to publication.

{% hint style="info" %}
Documents require the `document_management` [feature flag](../../configuration/settings/feature-flags.md) (on by default). See [Documents](../../concepts/documents.md) for the underlying model.
{% endhint %}

## Where documents live

- **Documents** — the reading catalogue: published documents as tiles, grouped by type, with search and type filters. This is where readers browse the published corpus.
- **Manage** (on the Documents page) opens the full document list, where you create and manage documents regardless of status.

## Create a document

From the document list, choose **New document** and set its **Document type** (Policy, Procedure, Charter, Record, Meeting minutes, Other), name, and domain. You land straight in the editor's **template picker**, where you can:

- **Start from scratch** — a blank document, or
- pick a **template** — the picker only offers templates matching the document's type and language.

## Write

The editor is a Markdown editor with a formatting toolbar (bold, italic, headings, lists, quote, code, link, table) and a live **preview** toggle. Two things worth knowing:

- **Link to document** inserts a link to another document. These links become the **References / Referenced by** panels automatically — see [Documents → References](../../concepts/documents.md#references).
- **Save draft** stores an increment as a new revision; the diff between the last loaded state and your current edits is tracked as you work.

## Review and publish

Each language version moves through **Draft → In review → Change requested → Validated → Published → Deprecated**:

{% stepper %}
{% step %}
### Submit for Review
From a draft, **Submit for Review** hands the document to a reviewer.
{% endstep %}

{% step %}
### Approve or Request changes
A reviewer either **Approves** the revision (→ Validated) or uses **Request changes** to send it back with reviewer comments (→ Change requested).
{% endstep %}

{% step %}
### Publish
**Publish** makes the validated revision the live version and renders a PDF snapshot. Previous published revisions are deprecated automatically.
{% endstep %}
{% endstepper %}

The **Version history** sidebar lists every revision; you can read any past version and diff two of them (see [Policies → Diff between revisions](../../concepts/policies.md#diff-between-revisions)).

## Add a language

Use **Add translation** to create another language version of the same document. Each language has its own lifecycle and revisions, so a translation can stay in draft while the original is published. One language is the default (used for the catalogue title and status).

## Upload instead of authoring

If the document already exists as a file, choose **Upload document** on the Documents page instead. The uploaded file (e.g. a signed PDF) runs through the same lifecycle and version history, but is served as-is rather than rendered from Markdown. You can upload a new version at any time.

## Export

**Export PDF** produces a PDF of the current document. On the PRO plan the PDF layout (cover page, header/footer, branding) can be customised — see [Custom templates → Document layout templates](../../configuration/settings/custom-templates.md#document-layout-templates).

## Related

- [Documents](../../concepts/documents.md)
- [Document templates](document-templates.md)
- [Policies](../../concepts/policies.md)
