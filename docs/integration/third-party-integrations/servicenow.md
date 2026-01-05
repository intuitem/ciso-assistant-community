---
description: ServiceNow Integration Guide
---

# ServiceNow

This guide details how to configure the bidirectional synchronization between **CISO Assistant** and **ServiceNow**. This integration allows you to:

* Automatically create ServiceNow records (e.g. GRC Controls) from CISO Assistant.
* Sync updates (Status, Priority, etc.) from CISO Assistant to ServiceNow.
* Receive real-time updates from ServiceNow back into CISO Assistant via Webhooks.

For now, you are only able to sync CISO Assistant's applied controls to a ServiceNow table.

***

### Prerequisites

Before starting, ensure you have:

1. **ServiceNow Credentials:** A service account with permissions to read/write to your target table (e.g., `grc_control`) and access the REST API.
2. **ServiceNow Admin Access:** Required to create **Outbound REST Messages** and **Business Rules** for the inbound sync.
3. **CISO Assistant Details:**
   * Your Instance URL.
   * The **Webhook Secret** generated in your Integration Configuration panel.

***

### Part 1: Outgoing Sync

First, configure CISO Assistant to connect to your ServiceNow instance.

1. **Create Integration:**
   * Go to **Settings > Integrations**.
   *   Add a new **ServiceNow** integration.<br>

       <figure><img src="../../.gitbook/assets/image (65).png" alt=""><figcaption></figcaption></figure>
2. **Connection Details:**
   * **Instance URL:** Enter your full instance URL (e.g., `https://dev12345.service-now.com`).
   * **Username/Password:** Enter the credentials for the service account.
   *   You can test the connection to your ServiceNow instance by pressing the **Test Connection** button

       <figure><img src="../../.gitbook/assets/image (67).png" alt=""><figcaption></figcaption></figure>
3. **Discovery & Mapping:**
   * **Target Table:** Select the ServiceNow table you want to sync with (e.g., `Control [grc_control]`).
   * **Field Mapping:** Map CISO Assistant fields (Name, Description, Status) to the corresponding ServiceNow columns.
   *   **Value Mapping:** For "Choice" fields like **Status** and **Priority**, map your local values (e.g., `In Progress`) to the specific ServiceNow logic (e.g., `2 - Work in Progress`).<br>

       <figure><img src="../../.gitbook/assets/image (68).png" alt=""><figcaption></figcaption></figure>
4. **Save**

***

### Part 2: Incoming Sync

If you with to receive updates from ServiceNow, you first have to enable incoming sync in the ServiceNow integration settings panel.

### Configure incoming sync in CISO Assistant

1. **Generate** a shared secret.
2. This secret is only shown once, make sure you **Copy** it before proceeding.

<figure><img src="../../.gitbook/assets/image (69).png" alt=""><figcaption></figcaption></figure>

### Configure ServiceNow

To receive updates _from_ ServiceNow, you must configure a **Business Rule** that pushes data to CISO Assistant.

#### Create the Outbound REST Message

This defines _where_ ServiceNow sends the data.

1. Log in to ServiceNow.
2.  Navigate to **System Web Services > Outbound > REST Message**.<br>

    <figure><img src="../../.gitbook/assets/image (70).png" alt=""><figcaption></figcaption></figure>
3. Click **New**.
4. Configure the message:
   * **Name:** `CISO_Assistant_Sync`
   * **Endpoint:** Paste your **Webhook URL** from Part 1.
   * **Authentication:** `No Authentication` (we will use a header token).
5. Click **Submit**.
6. **Crucial:** Re-open the record and note the **API Name** field (e.g., `x_12345_ciso_assistant_sync` or just `CISO_Assistant_Sync`). You will need this for the script.

#### Configure the HTTP Method

1. In the REST Message record, scroll to the **HTTP Methods** list.
2. Create a **New** method (or edit the default one):
   * **Name:** `POST_Event`
   * **HTTP Method:** `POST`
   * **Endpoint:** Paste your **Webhook URL** again.
3. **Add Authentication Header:**
   * Scroll to **HTTP Request Headers**.
   * Add a new row:
     * **Name:** `X-CISO-Secret`
     * **Value:** Paste your **Webhook Secret** from Part 1.
   * Add a second row:
     * **Name:** `Content-Type`
     * **Value:** `application/json`
4. Click **Submit**.

<figure><img src="../../.gitbook/assets/image (71).png" alt=""><figcaption></figcaption></figure>

#### Create the Business Rule

This triggers the sync whenever a record changes.

1. Navigate to **System Definition > Business Rules**.\
   ![](<../../.gitbook/assets/image (72).png>)
2. Click **New**.
3. **Name:** `Push to CISO Assistant`.
4. **Table:** Select the same table you chose in Part 1 (e.g., `Control`).
5. **Advanced:** Check this box.
6. **When to run:**
   * **When:** `After`
   * **Insert:** Checked.
   * **Update:** Checked.
   *   **Filter Conditions:** (Recommended) Add conditions to reduce noise, e.g., `State changes` OR `Priority changes`.\
       <br>

       <figure><img src="../../.gitbook/assets/image (74).png" alt=""><figcaption></figcaption></figure>
7. **Advanced (Script):** Paste the following code.

{% hint style="warning" %}
Replace `'CISO_Assistant_Sync'` in line 4 with the **API Name** you noted in Step 2.1.
{% endhint %}

```js
(function executeRule(current, previous) {

    try {
        // Initialize REST Message ('API Name', 'Method Name')
        // REPLACE 'CISO_Assistant_Sync' with your actual API Name if different!
        var r = new sn_ws.RESTMessageV2('CISO_Assistant_Sync', 'POST_Event');

        // Determine Event Type
        var eventType = 'sn_update';
        if (current.operation() == 'insert') {
            eventType = 'sn_create';
        } else if (current.operation() == 'delete') {
            eventType = 'sn_delete';
        }

        // Build Payload (Mapping raw database values)
        var payload = {
            "event": eventType,
            "sys_id": current.getValue("sys_id"),
            "number": current.getValue("number"),
            "short_description": current.getValue("short_description"),
            "description": current.getValue("description"),
            "state": current.getValue("state"),
            "priority": current.getValue("priority"),
            "due_date": current.getValue("due_date"),
            "sys_updated_on": current.getValue("sys_updated_on")
        };

        // Send Request
        r.setRequestBody(JSON.stringify(payload));
        var response = r.execute();
        
        // Log Errors
        var httpStatus = response.getStatusCode();
        if (httpStatus < 200 || httpStatus >= 300) {
            gs.error("CISO Sync Failed: " + httpStatus + " " + response.getBody());
        }

    } catch (ex) {
        gs.error("CISO Sync Error: " + ex.message);
    }

})(current, previous);
```

Click **Submit**.<br>

<figure><img src="../../.gitbook/assets/image (75).png" alt=""><figcaption></figcaption></figure>

***

### Usage

Once the integration is configured and enabled, CISO Assistant will start synchronizing applied controls with ServiceNow records.

* For each applied control, a new record will be created in the configured ServiceNow table if you check 'Create remote object' in the applied control creation form.
* The ServiceNow record will contain information from the applied control, such as its name, description, and status.
* A link to the ServiceNow record will be displayed on the applied control page in CISO Assistant.

The synchronization is automatic. Any update on an applied control in CISO Assistant will be reflected in the corresponding ServiceNow record.

#### Attaching an applied control to a ServiceNow record

There are several ways to link an applied control to a ServiceNow record:

* **On applied control creation:**
  * Open the `Integrations` dropdown menu located at the bottom of the form
  * Select the `ServiceNow` integration provider
  * Check the `Create remote object` checkbox.
  * This will create a ServiceNow record on the board specified in CISO Assistant's ServiceNow integration settings. This record will then be linked to the applied control.

<figure><img src="../../.gitbook/assets/image (76).png" alt=""><figcaption></figcaption></figure>

* **On an existing applied control:**
  * Go to an applied control's edit form
  * Open the `Integrations` dropdown menu located at the bottom of the form
  * Select the `ServiceNow` integration provider
  * Select the ServiceNow record you wish to link to your applied control.

<figure><img src="../../.gitbook/assets/image (77).png" alt=""><figcaption></figcaption></figure>

#### Notes:

* The default sync period on SaaS is at 60 seconds.
* The API needs to be enabled and the instance reachable. If you're on SaaS plan, you can reach the support to do so.
* For on-premises deployments, you might want to adapt `scheduler-interval` value on Huey

### Verification & Troubleshooting

#### How to Verify

1. Create a new Control in CISO Assistant. Check ServiceNow to see if the record appears.
2. Update the **State** of that record in ServiceNow. Refresh CISO Assistant to see the status change.

#### Common Errors

| **Symptom**                         | **Cause**       | **Solution**                                                                                                                        |
| ----------------------------------- | --------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **HTTP 401/403 in ServiceNow Logs** | Secret Mismatch | Ensure the `X-CISO-Secret` header in ServiceNow matches the Webhook Secret in CISO Assistant exactly.                               |
| **"RESTMessageV2 is not defined"**  | Scope Issue     | Ensure the script uses the correct **API Name** for the REST Message (e.g., `x_scope_ciso_sync`).                                   |
| **CISO Assistant doesn't update**   | Missing Filter  | Check the Business Rule filter conditions. Ensure the change you made (e.g., just changing a description) is covered by the filter. |
| **Dropdowns empty in Setup**        | Permissions     | Ensure the service account has read access to `sys_db_object` and `sys_dictionary`.                                                 |
