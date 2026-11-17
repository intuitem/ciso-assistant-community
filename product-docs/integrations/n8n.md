---
description: >-
  Automate CISO Assistant from n8n workflows with the official community node:
  read and update audits, evidence, risks, incidents and more, or hand the node
  to an AI agent as a tool.
---

# n8n node

Compatible with: SaaS or on-premises, CE or Pro. Requires a self-hosted n8n instance.

The official node is published on npm as [`@intuitem/n8n-nodes-ciso-assistant`](https://www.npmjs.com/package/@intuitem/n8n-nodes-ciso-assistant). Each release is built from this repository by GitHub Actions and carries an npm provenance statement that links it to the commit it was built from.

{% hint style="warning" %}
The unscoped `n8n-nodes-ciso-assistant` package on npm is not maintained by intuitem. Install the `@intuitem/` one.
{% endhint %}

### Install the node

You need to be the owner or an admin of the n8n instance.

1. In n8n, go to **Settings → Community Nodes**.
2. Select **Install**.
3. Enter the npm package name `@intuitem/n8n-nodes-ciso-assistant`.
4. Tick the box acknowledging the risks of installing community code, then select **Install**.
5. Open a workflow, add a node and search for **CISO Assistant**.

To upgrade later, go back to **Settings → Community Nodes**, where n8n shows when an update is available.

n8n Cloud only lists community nodes that n8n has verified, and this one isn't verified yet. For queue mode or installs without the UI, see the [n8n installation guide](https://docs.n8n.io/integrations/community-nodes/installation/).

### Create the credential

1. Generate a Personal Access Token in CISO Assistant: [Generating a PAT](pat.md). It is displayed only once.
2. In n8n, create a **CISO Assistant API** credential:
   * **Personal Access Token (PAT)**: the token.
   * **API URL**: your instance's API base URL, with `/api` and without a trailing slash, e.g. `https://ciso-assistant.example.com/api`.
   * **Skip TLS Verification**: leave it off. Only turn it on for a self-signed certificate on a network you trust.
3. Save. n8n tests the credential by calling the API with the token.

The node acts as the token's owner, so a workflow only sees and changes what that user can. For unattended workflows, use a [service account](service-accounts.md) rather than a personal account.

### What the node can do

Pick a **Resource**, then an **Operation**:

| Resource | Operations |
| --- | --- |
| Applied Control, Asset, Data Breach, Finding, Right Request, Risk Scenario, Security Exception, Task Definition | Create, Get, Get by Name, Get Many, Update |
| Incident, Task Occurrence, Vulnerability | Create, Get, Get Many, Update |
| Domain, Entity, Entity Assessment, Perimeter, Solution | Create, Get, Get by Name, Get Many |
| Representative | Create, Get, Get Many |
| Findings Tracking | Create, Get, Get by Name, Get by Ref ID, Get Many, Update |
| Audit | Get, Get by Name, Get by Ref ID, Get Many, Initiate, Get Requirement Assessment, List Requirement Assessments, Update Requirement Assessment |
| Risk Assessment | Get, Get by Name, Get by Ref ID, Get Many, Initiate |
| Evidence | Create, Get, Get by Name, Get Many, Submit Revision, List Revisions, Update Envelope |
| Framework, Risk Matrix | Get, Get Many |
| System | Get Build Info, Get Many Users, Get User by Email |

Every resource except System has **Get** (by ID) and **Get Many**. Get Many fetches every page when **Return All** is on, otherwise up to **Limit** records. Names in "Get by Name" operations are case-sensitive, dates use ISO 8601, and IDs must be UUIDs.

The node can also be attached to an n8n **AI Agent** as a tool, so the agent can look up or update CISO Assistant objects itself.

### Examples

* **Evidence collection**: on a schedule, export a report from another tool and push it with **Evidence → Submit Revision** (Revision Type **File Upload**, Binary Property set to the field holding the file).
* **Audit from a scanner**: map each scanner check to a requirement ref ID, then run **Audit → Update Requirement Assessment** to set its result and observation.
* **Incident intake**: create an **Incident** from a ticketing or alerting webhook.

### Node versions

New nodes use version 2: Get Many and lookup operations output one item per record, so the next node runs once per object, and no match means no items. Nodes created before version 2 stay on version 1, which outputs a single item with `count` and `results`. To move a node to version 2, delete it, add it again and update any downstream expressions that read `results`.

On version 2, **Update Requirement Assessment** leaves status, result and score unchanged unless you set them, so you can update the observation alone.

### Troubleshooting

* **Credential test fails with 401**: the token is wrong, expired or revoked. Generate a new one.
* **Credential test fails with another error**: check that the API URL ends with `/api` and has no trailing slash.
* **Certificate errors**: install a certificate n8n trusts, or, on a trusted network only, turn on **Skip TLS Verification**.
* **Two CISO Assistant nodes in the panel**: an n8n started with `N8N_CUSTOM_EXTENSIONS` pointing at a local build also loads that copy. Remove the variable to keep only the installed package.
