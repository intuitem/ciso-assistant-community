---
description: GLPI Integration Guide
---

# GLPI

The GLPI integration synchronizes applied controls from CISO Assistant with assistance items in GLPI: tickets, changes or problems. It lets you:

* Create a GLPI item from an applied control, or link an applied control to an existing item.
* Push updates (name, description, status, priority, ETA) from CISO Assistant to GLPI.
* Receive updates from GLPI back into CISO Assistant through GLPI webhooks.

## Requirements

* **GLPI 11 or later.** The integration uses the high-level REST API (version 2), which GLPI 10 does not provide. It has been tested against GLPI 11.0 and 12.0.
* A GLPI administrator, to enable the API and create an OAuth client and a webhook.
* A GLPI user for the integration. CISO Assistant acts as this user, so its profile decides which items can be read, created and updated.
* CISO Assistant must be able to reach GLPI over HTTPS. For incoming sync, GLPI must be able to reach CISO Assistant.

{% hint style="info" %}
The instance URL must resolve to a public address. If your GLPI is on a private network, start the CISO Assistant backend with `ALLOW_PRIVATE_NETWORK_REQUESTS=True`.
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
2. Enable **Outgoing sync** and fill in the connection details:
   * **Instance URL:** the base URL of your GLPI instance, for example `https://glpi.example.com`.
   * **Client ID** and **Client secret:** the values from the OAuth client.
   * **Username** and **Password:** the GLPI user the integration acts as.
3. Press **Test Connection**. A successful test proves both the OAuth client and the user's API access.
4. **Save**. The mapping section appears once the configuration is saved.

### Map the fields

1. **Target Table:** pick the GLPI item type to sync with: tickets, changes or problems.
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
* **Linking an existing item:** in the applied control's edit form, open `Integrations`, select the GLPI configuration and pick the item. You can search by name or by GLPI id. Items in the trash and items already linked are not offered.
* **Updating an applied control** pushes the changed fields to the linked item.
* **Updating the item in GLPI** updates the applied control. GLPI sends webhooks from a queue, so changes arrive with a short delay (about a minute with GLPI's default settings).

The applied control page shows the linked GLPI id, the last sync time and its status.

## Good to know

* GLPI stores the item description as rich text. CISO Assistant sends plain paragraphs and reads formatted content back as plain text.
* Items created directly in GLPI are not imported into CISO Assistant.
* Assets are not synchronized with GLPI yet.
