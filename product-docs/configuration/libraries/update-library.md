---
description: Publish a new version of a custom library and apply it where needed
---

# Update a library

To update a custom library, make changes in its Excel file and upload the new version to CISO Assistant. You can upload the updated Excel file directly. Converting it to YAML before importing is completely optional.

{% hint style="info" %}
Before updating a library, it is strongly recommended to keep a backup copy of the original Excel or YAML file in a safe place.
{% endhint %}

## Publish a new version

1. Edit the library's Excel (`.xlsx`) file.
2. Increase `version` in the `library_meta` sheet. Keep the library's `urn` and every other type of identifiers (e.g. `ref_id`) of existing content stable so CISO Assistant can recognize the library and preserve references to its existing requirements.
3. Upload the updated Excel (`.xlsx`) file as described in [Import a library](import-library.md). If you prefer, convert it to YAML first with [`convert_library_v2.py`](https://github.com/intuitem/ciso-assistant-community/blob/main/backend/scripts/convert_library_v2.py), then upload the generated `.yaml` file.
4. After the upload, follow [Update a library from the catalog](#update-a-library-from-the-catalog) below to load the new version in your instance.

## Update a library from the Catalog

Use this action to load a newer library version into your instance. This applies both to an updated custom library you imported using the steps above and to a built-in library update made available after a CISO Assistant upgrade:

1. Go to **Governance > Libraries**.
2. Click **Update available** to filter the list to libraries with a newer version.
3. In the relevant row, click the <img src="../../.gitbook/assets/update_library_button.png" alt="Green circular button with an upward arrow" data-size="line"> button at the far right.

![Libraries page showing the Update available filter and the update action for a library](../../.gitbook/assets/update_library.png)

{% hint style="warning" %}
Updating a library from the catalog also updates the content of all objects in your instance that are linked to that library. Always click the library in the catalog and inspect its updated content before starting the update.
{% endhint %}
