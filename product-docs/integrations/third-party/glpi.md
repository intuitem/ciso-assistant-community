---
description: GLPI Integration Guide
---

# GLPI

The GLPI integration synchronizes CISO Assistant objects with GLPI items:

* **Applied controls** with assistance items: tickets, changes or problems.
* **Assets** with GLPI assets, for example computers, software or appliances. See [Syncing assets](#syncing-assets).

It lets you:

* Create a GLPI item from an applied control, or link an applied control to an existing item.
* Push updates (name, description, status, priority, ETA) from CISO Assistant to GLPI.
* Receive updates from GLPI back into CISO Assistant through GLPI webhooks.

## Requirements

* **GLPI 11 or later.** The integration uses the high-level REST API (version 2), which GLPI 10 does not provide. It has been tested against GLPI 11.0.0, 11.0.13 and 12.0.2.
* A GLPI administrator, to enable the API and create an OAuth client and a webhook.
* A GLPI user for the integration. CISO Assistant acts as this user, so its profile decides which items can be read, created and updated.
* CISO Assistant must be able to reach GLPI over HTTPS. For incoming sync, GLPI must be able to reach CISO Assistant.

{% hint style="info" %}
The instance URL must resolve to a public address. If your GLPI is on a private network, start the CISO Assistant backend with `ALLOW_PRIVATE_NETWORK_REQUESTS=True`. This setting applies to the whole backend, not only to GLPI, and it also lifts the HTTPS requirement: keep the GLPI URL on HTTPS.
{% endhint %}

## Part 1: Outgoing sync

### Prepare GLPI

1. In **Setup > General > API**, turn on **Enable API**. This is the high-level API, not the legacy one.
2. In **Setup > OAuth clients**, add a client:
   * **Grants:** `Password`
   * **Scopes:** `api`
3. Copy the **Client ID** and the **Client secret**. GLPI shows the secret only once.

### Configure CISO Assistant

1. Go to **Settings > Integrations** and open **GLPI**.
2. Enable **Outgoing sync** and fill in the connection details. They are needed for incoming sync too, which reads items back from GLPI:
   * **Instance URL:** the base URL of your GLPI instance, for example `https://glpi.example.com`.
   * **Client ID** and **Client secret:** the values from the OAuth client.
   * **Username** and **Password:** the GLPI user the integration acts as.
3. Press **Test Connection**. A successful test proves both the OAuth client and the user's API access. It does not check the user's rights on the items themselves: make sure its GLPI profile can read, create and update the item types you sync with.
4. **Save**. The mapping section appears once the configuration is saved.

### Map the fields

1. **Target Table:** pick the GLPI item type to sync with: tickets, changes or problems. Once objects are linked through the configuration, the item type can no longer be changed: unlink them first. GLPI webhooks are tied to an item type, so after changing it, replace them with webhooks for the new type.
2. **Field Mapping:** CISO Assistant reads the fields your GLPI version exposes and pre-fills the usual mapping:

| CISO Assistant | GLPI |
| -------------- | ---- |
| Name | `name` |
| Description | `content` |
| Status | `status` |
| Priority | `priority` |
| ETA | `resolution_date` |

3. **Value Mapping:** status and priority are pre-filled when the matching GLPI value exists for the item type:

| CISO Assistant | GLPI ticket |
| -------------- | ----------- |
| To do | New |
| In progress | Processing (assigned) |
| On hold | Pending |
| Active | Solved |
| P1 | Very high |
| P2 | High |
| P3 | Medium |
| P4 | Low |

4. Adjust the rows to your process, then **Save**. Use **Refresh schema** after a GLPI upgrade or a change to its fields.

5. **Asset mapping (optional):** below the applied control mappings, the **Assets** section works the same way:
   * **Target Table:** pick the GLPI asset type: computer, monitor, network equipment, peripheral, phone, printer, software, software license, certificate, appliance, rack, enclosure or PDU.
   * **Field Mapping:** map the asset fields you want to sync: Name, Description, ID, Type, Reference link and Observation. Name, Description (to `comment`) and ID (to `otherserial`, the inventory number) are suggested when the asset type has them.
   * Leave this section empty if you don't want to sync assets. Assets are only synced once a target table is set and at least one field is mapped, and only the fields you map.

A local value with no mapping is not pushed. With the default mapping, the GLPI values that have no row of their own are still understood on incoming sync: `Processing (planned)` is read as In progress, `Closed` as Active, `Very low` as P4 and `Major` as P1.

## Part 2: Incoming sync

GLPI sends changes through its webhooks. Each webhook covers one item type and one event.

### Create the webhooks in GLPI

1. In **Setup > Webhooks**, add a webhook:
   * **Itemtype:** the item type you selected as target table.
   * **Event:** `Update`
   * **URL:** the **Webhook Endpoint URL** shown on the GLPI integration page in CISO Assistant, prefixed with the address of your CISO Assistant API.
   * **HTTP method:** `POST`
   * Keep the default payload.
2. Open the webhook's **Security** tab and copy its **Secret**.
3. Optionally add a second webhook for the `Delete` event, with the same URL and the same secret. CISO Assistant then flags the link when the GLPI item is moved to the trash.
4. If you sync assets, add the same webhooks for the asset type, with the same URL and the same secret.

### Configure CISO Assistant

1. On the GLPI integration page, enable **Incoming sync**.
2. Paste the secret into **Webhook Secret**.
3. **Save**.

CISO Assistant rejects any request whose signature does not match this secret.

{% hint style="warning" %}
GLPI refuses to call addresses it considers unsafe, which includes private networks. If CISO Assistant is not on a public address and GLPI's `webhook.log` reports the URL as unsafe or blocked, allow it in GLPI's `config/local_define.php`: with `GLPI_SERVERSIDE_URL_ALLOWLIST` on GLPI 11, or by adding `Webhook::class` to `GLPI_SERVERSIDE_URL_ALLOWED_PRIVATE_NETWORKS_CONTEXTS` on GLPI 12.
{% endhint %}

## What happens once configured

* **Creating an applied control:** open the `Integrations` section at the bottom of the form, select the GLPI configuration and tick `Create remote object`. A GLPI item is created and linked.
* **Linking an existing item:** in the applied control's edit form, open `Integrations`, select the GLPI configuration and pick the item. You can search by name or by GLPI id. Items in the trash and items already linked are not offered. Linking copies nothing in either direction: from then on, each side follows the other's changes.
* **Updating an applied control** pushes the changed fields to the linked item.
* **Updating the item in GLPI** updates the applied control. The webhook only signals the change: CISO Assistant then reads the item from GLPI and applies the fields that changed there since the last sync. An edit made in CISO Assistant at the same moment on another field is kept and pushed. If GLPI cannot be reached at that moment, nothing is applied and the control catches up with the next change. GLPI sends webhooks from a queue, so changes arrive with a short delay (about a minute with GLPI's default settings). If they never arrive, check that the `queuedwebhook` automatic action is enabled and running in GLPI, and look at the webhook queue.

The applied control page shows the linked GLPI item (its type and id, for example `Ticket:42`), the last sync time and its status.

### Syncing assets

Asset sync works differently from applied controls:

* **Every new asset is pushed.** Once the **Assets** section has a target table, creating an asset in CISO Assistant creates an item of that type in GLPI. There is no `Create remote object` checkbox.
* **Existing assets are pushed when a synced field changes.** Assets created before you set the table are not sent in bulk. Each one is created in GLPI the first time one of its mapped fields is edited.
* **Linking to an existing item is API-only.** Update the asset through the API (`PATCH /api/assets/<id>/`) with `integration_config` set to the integration's ID and `remote_object_id` set to the GLPI id of the item. Later edits then update that item instead of creating a new one.
* **Incoming sync only updates linked assets.** Changes made in GLPI are applied to the linked asset. Items created in GLPI do not create assets in CISO Assistant, so this is not an inventory import.
* **Only plain fields can be mapped.** GLPI dropdowns such as status, type, location or manufacturer are not offered, and neither are relations between assets.
* **One asset type per configuration.** As for applied controls, it can no longer be changed once assets are linked, even after clearing the target table.

## Good to know

* GLPI stores the item description as rich text. CISO Assistant sends plain paragraphs and reads formatted content back as plain text.
* Items created directly in GLPI are not imported into CISO Assistant.
* Links store GLPI item types and ids. GLPI numbers each item type on its own, so ticket 12 and computer 12 can both be linked without being mixed up. Only change the instance URL when the new address serves the same GLPI instance, otherwise unlink the objects first.
* The ETA is synced from GLPI 11.0.2 on. GLPI 11.0.0 and 11.0.1 do not expose the date through their API, so it is left out there.
* Removing the ETA of an applied control does not remove the date in GLPI: its API cannot clear it.
* With the default mapping, the `In progress` status is not sent to a change: GLPI changes have no matching status. Pick one in **Value Mapping** if you want it synced.
* Custom asset definitions are not synchronized yet.
