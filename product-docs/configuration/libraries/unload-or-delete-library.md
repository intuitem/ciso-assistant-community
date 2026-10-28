---
description: Unload or delete a library from CISO Assistant
---

# Unload or delete a library

Unloading a library makes its content unavailable for use, but keeps the library in the catalog so you can load it again later. Deleting a library removes it from the catalog entirely. To use it again, you must re-import its Excel or YAML file into your instance.

## Unload a library

1. Open **Governance > Libraries** and find the library you want to unload.
2. In the relevant row, click the <img src="../../.gitbook/assets/unload_library_button.png" alt="Document with a minus sign: Unload library" data-size="line"> button at the far right.

![Libraries page with the Unload library button highlighted for a custom library](../../.gitbook/assets/unload_library.png)

{% hint style="warning" %}
Only administrators can see the unload button. It is hidden while an audit uses the library's Framework, a risk assessment or business impact analysis uses its risk matrix, or an assessment uses its threats or controls based on its reference controls. Delete or change those objects first.

If a loaded Mapping library depends on this library, the button still appears, but unloading fails because the library is in use. Unload the Mapping library first.

If you only want to update the library, follow [Update a library](update-library.md) instead.
{% endhint %}

## Delete a library

1. If the library is loaded, unload it first using the steps above.
2. In **Governance > Libraries**, find the library you want to delete.
3. In the relevant row, click the <img src="../../.gitbook/assets/delete_library_button.png" alt="Trash can: Delete library" data-size="line"> button at the far right.

![Libraries page with the Delete button highlighted for an unloaded custom library](../../.gitbook/assets/delete_library.png)

{% hint style="warning" %}
Libraries provided by CISO Assistant cannot be deleted from the catalog. If you want to import the library you are about to delete at a later time, keep a copy of its Excel or YAML file in a safe place before deleting it.
{% endhint %}
