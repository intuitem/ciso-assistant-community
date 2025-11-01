# Jira

### Overview

The Jira integration allows you to synchronize applied controls from CISO Assistant with issues in your Jira projects. This helps you track the implementation and status of your controls directly in Jira, leveraging your existing workflows.

When the integration is active, CISO Assistant will allow linking applied controls to Jira issues, or creating new issues when creating an applied control. Updates to the applied control in CISO Assistant will be reflected in the corresponding Jira issue, and vice-versa.

Two sync modes are available:

* **Incoming sync (pull):** Relies on webhooks to reflect changes made on a Jira issue to its linked applied control
* **Outgoing sync (push):** Pushes changes made on an applied control to its linked Jira issue through the Jira REST API

You can enable one or both of these modes.

### Prerequisites

* A CISO Assistant instance.
* A Jira Cloud service account with administrative privileges to create API tokens, outgoing webhooks and manage projects.
* Alignement between the jira status options and CISO Assistant options.







## Outgoing sync

### Configuration

To configure the integration, you will need to perform steps on both the Jira and CISO Assistant sides.

#### 1. Configure Jira

**Create a Jira API Token**

1. Log in to your Jira account.
2. Go to your Atlassian account settings: click on your profile picture in the bottom left, then "Profile". In the new page, click on "Manage your account".
3. In your Atlassian account page, navigate to **Security** > **API token**.
4. Click on **Create and manage API tokens**.
5. Click **Create API token**.
6. Give your token a descriptive label, for example, "CISO Assistant Integration".
7. Copy the generated API token. You will not be able to see it again. Store it in a safe place. You will need it to configure CISO Assistant.

<figure><img src="../../.gitbook/assets/image (39).png" alt=""><figcaption></figcaption></figure>

**Identify your Jira Project Key**

1. In Jira, go to the project you want to integrate with CISO Assistant.
2. The project key is a short identifier for your project (e.g., 'PROJ', 'CIS'). You can find it in the project details or in the URL.

<figure><img src="../../.gitbook/assets/image (41).png" alt=""><figcaption></figcaption></figure>

### **Incoming sync**

{% hint style="info" %}
This is only useful if you wish to enable incoming sync on CISO Assistant. Incoming sync requires outgoing ones.
{% endhint %}

* Log in to your Jira account
* Go to **System settings > WebHooks**
* Click the **+ Create WebHook** button on the top-right corner

#### 2. Configure CISO Assistant

1. Log in to your CISO Assistant instance.
2.  Navigate to the integrations settings page. Find the Jira integration section.

    <figure><img src="../../.gitbook/assets/image (46).png" alt=""><figcaption></figcaption></figure>
3. Configure outgoing sync:
   1. Enter the following information:
      * **Jira URL:** The URL of your Jira instance (e.g., `https://your-company.atlassian.net`).
      * **Jira Username/Email:** The email address you use to log in to Jira.
      * **Jira API Token:** The API token you created in the previous step.
      * **Jira Project Key:** The key of the Jira project you want to synchronize with.
4. Configure incoming sync
   1.  Enter the following information:

       *   **Webhook secret:** The webhook secret you have generated when configuring your outgoing webhook on Jira.\


           <figure><img src="../../.gitbook/assets/image (44).png" alt=""><figcaption></figcaption></figure>
       * **URL:** This is the URL where CISO Assistant will receive incoming webhooks from Jira. It is of the following form: `<API_URL/api/integrations/webhook/<INTEGRATION_CONFIG_ID>/` . You can find your webhook URL on the bottom of CISO Assistant's Jira integration settings, located in **Extra > Settings > Integrations > Jira**
         * Note that the configuration object must exist for you to see the webhook endpoint URL. If you do not see it at the bottom of the page, finish filling the settings form and press `Save`. It will then appear.
       *   Tick the issue **created, updated, deleted** events. Other events are not tracked.

           <figure><img src="../../.gitbook/assets/image (47).png" alt=""><figcaption></figcaption></figure>

       <figure><img src="../../.gitbook/assets/image (42).png" alt=""><figcaption></figcaption></figure>
5. Save the configuration

<figure><img src="../../.gitbook/assets/image (45).png" alt=""><figcaption></figcaption></figure>

### Usage

Once the integration is configured and enabled, CISO Assistant will start synchronizing applied controls with Jira issues.

* For each applied control, a new issue will be created in the configured Jira project if you check 'Create remote object' in the applied control creation form.
* The Jira issue will contain information from the applied control, such as its name, description, and status.
* A link to the Jira issue will be displayed on the applied control page in CISO Assistant.

The synchronization is automatic. Any update on an applied control in CISO Assistant will be reflected in the corresponding Jira issue.

#### Attaching an applied control to a Jira issue

There are several ways to link an applied control to a Jira issue:

* **On applied control creation:**
  * Open the `Integrations` dropdown menu located at the bottom of the form
  * Select the `Jira` integration provider
  * Check the `Create remote object` checkbox.
  * This will create a Jira issue on the board specified in CISO Assistant's Jira integration settings. This issue will then be linked to the applied control.

<figure><img src="../../.gitbook/assets/image (50).png" alt=""><figcaption></figcaption></figure>

* **On an existing applied control:**
  * Go to an applied control's edit form
  * Open the `Integrations` dropdown menu located at the bottom of the form
  * Select the `Jira` integration provider
  * Select the Jira issue you wish to link to your applied control.

<figure><img src="../../.gitbook/assets/image (49).png" alt=""><figcaption></figcaption></figure>

#### Outgoing sync (Push)

* Creating an applied control
* Updating an applied control

#### Incoming sync (Pull)

* `jira:issue_created`
* `jira:issue_update`
* `jira:issue_deleted`



#### Notes:

* The default sync period on SaaS is at 60 seconds.
* For on-premises deployments, you might want to adapt `scheduler-interval` value on Huey
