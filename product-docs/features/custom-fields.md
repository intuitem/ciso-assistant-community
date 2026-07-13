---
description: Org-defined typed fields on your objects — filterable, searchable, per-domain
---

# Custom fields

{% hint style="info" %}
Custom fields are a **PRO** capability, gated by the `custom_fields` feature flag (off by default). See [Feature flags](../configuration/settings/feature-flags.md).
{% endhint %}

The built-in models cover most needs, but every organisation has attributes of its own — an asset's data classification, a control's vendor, a project's business sponsor code. Custom fields let an administrator define typed, validated fields on selected objects, set values per object, and then filter, search, and report on them like any native field.

Custom fields are available on **Projects**, **Assets**, and **Applied controls** (policies share the applied-control fields).

{% hint style="warning" %}
**Use them sparingly.** CISO Assistant's built-in data model is already rich — reach for a custom field only when an attribute is genuinely specific to your organisation. Over-using them fragments your data and your reporting, and that complexity is yours to maintain.

If an attribute is generic enough to be useful to everyone, **tell us** rather than approximating it with a custom field — we'd much rather add it as a first-class, properly-modelled field. [Get in touch](https://intuitem.com/) or open an issue.

**No automatic migration.** If a field you added as a custom field later becomes a native platform field, there is **no automatic data migration** — moving the existing values onto the native field is up to you, manually or via the [API](../integrations/api.md).
{% endhint %}

## For users

- **Where it lives.** Define and manage fields from the sidebar under **Extra → Custom fields** (`/custom-fields`). Once defined, fields appear directly on the create/edit form and detail page of the objects they target.
- **When to use it.** Whenever you need to capture an org-specific attribute that isn't part of the built-in object — without waiting for a code change.
- **How to use it.**
  1. Open **Custom fields** and add a definition. You choose the **Model** it attaches to, the **Domain** it applies to, a **Key** (the stable identifier), a **Label**, an optional **Help text**, and a **Field type**.
  2. Pick the **Field type**: **Text**, **Number**, **Date**, **Boolean**, **Choice**, or **Multiple choice**. Choice and multiple-choice fields take a list of options (**Add choice**).
  3. Tune behaviour with the flags — **Required**, **Visible**, **Searchable**, **Filterable** — and **Order** (where it sits among other custom fields).
  4. Open any targeted object. Custom fields show in a collapsible **Custom fields** section on the form; fill them in and save. The values then appear on the object's detail page.
- **What it gives you.**
  - **Domain scoping.** A field set to the **Global** domain applies to every object of that model; a field set to a specific domain applies only within that domain and its sub-domains.
  - **In tables.** Visible custom fields are offered as opt-in columns in the column picker; choice and boolean fields become table filters; and text-type fields marked **Searchable** are matched by the table search box alongside the native fields.
  - **Translations.** Labels, help text, and choice labels can be translated per locale, so the field shows in each user's language.

## For implementers

- **Surface area.** A dedicated `custom_fields` Django app with a typed Entity-Attribute-Value design: `CustomFieldDefinition`, `CustomFieldChoice`, and `CustomFieldValue` (one typed column per type; one row per selected choice for multiple-choice). Host models opt in through `CustomFieldsMixin` — currently `pmbok.Project`, `core.Asset`, and `core.AppliedControl` (`Policy` inherits it as an `AppliedControl` proxy). Definitions are managed at `/api/custom-fields/`; values are exposed and written as a nested `custom_fields` object on each host's serializer.
- **Key integration points.** Tables read it three ways — dynamic `cf__<key>` filters, opt-in columns flattened from the values, and search over searchable text values; the generic detail view renders a read-only panel; the object forms render the editable section. All of it resolves the field set for an object from its domain.
- **Gotchas.**
  - **Folder scoping drives applicability** — a definition applies to an object only when its domain is the object's domain, an ancestor, or **Global**.
  - **Key is immutable** after creation, and a key resolves to a single type per model — you can't have the same key be a choice in one domain and a number in another.
  - **Searchable** is allowed only on text-backed types (text, choice, multiple-choice); the others have no effect and the checkbox is hidden.
  - A field's **type can't be changed once values exist**, and a **required** field can't be cleared with an empty value.
  - Deleting a definition **deletes its stored values**.
- **Configuration.** The `custom_fields` feature flag (enterprise, off by default). Defining and editing fields requires the **Custom field definition** management permissions (Domain manager and Administrator by default); other roles can read definitions so forms render.

## Status

- **Edition:** enterprise
- **Feature flag:** `custom_fields` (default off)
- **Hosts:** Projects, Assets, Applied controls (and Policies)

## Related

- [Working with tables](working-with-tables.md) — columns, filters, and search that surface custom fields.
- [Terminology](../concepts/terminology.md) — controlled vocabularies, the catalogue's other org-defined metadata.
- [Feature flags](../configuration/settings/feature-flags.md) · [Community vs PRO](../introduction/editions.md)
