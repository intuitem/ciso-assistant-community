# Outgoing webhooks

<!--toc:start-->

- [Outgoing webhooks](#outgoing-webhooks)
  - [Overview & goals](#overview-goals)
  - [Technical specification & tradeoffs](#technical-specification-tradeoffs)
    - [Data models](#data-models)
    - [Architecture: the registry pattern](#architecture-the-registry-pattern)
    - [Event triggering](#event-triggering)
      - [Rationale](#rationale)
    - [Huey task execution](#huey-task-execution)
    - [Security & consumer management](#security-consumer-management)
    - [Payload](#payload)
      - [Payload structure](#payload-structure)
      - [Payload strategy](#payload-strategy)
    - [Webhook headers](#webhook-headers)
    - [Verifying signatures (MVP)](#verifying-signatures-mvp)
  - [MVP limitations & future iterations](#mvp-limitations-future-iterations)
  <!--toc:end-->

## Overview & goals

This document outlines the MVP implementation for **Outgoing Webhooks** in CISO Assistant.

- **Goal:** To provide a secure, reliable, and straightforward way for users to subscribe to events within the platform (e.g., `appliedcontrol.created`) and receive notifications at an external HTTP endpoint.
- **Foundation:** This implementation **MUST** adhere to the **Standard Webhooks v1.0.0** specification.
- **MVP Stack:**
  - **Backend:** Django / DRF
  - **Queueing:** Huey (with SQLite backend)
  - **Signatures:** HMAC-SHA256 (`v1`)
  - **Payloads:** "Thin" (ID-only) or "Full" (entire object) JSON

---

## Technical specification & tradeoffs

### Data models

We will introduce one primary model, `WebhookEndpoint`, which will contain the consumer endpoint URL, the shared secret (MVP), and a secondary model, `WebhookEventType` which will store the types of events to listen to (e.g. `["appliedcontrol.created", "appliedcontrol.updated", "appliedcontrol.deleted"]`).

### Architecture: the registry pattern

To keep our application logic decoupled, we will use a **Registry Pattern** to manage webhook dispatch logic, rather than mixins or model-level overrides.

This pattern consists of three parts:

1. **Registry (`webhooks/registry.py`):** A global object that maps registered Django models (like `AppliedControl`) to a configuration class.
2. **Config (`webhooks/config.py`):** A simple class that defines _how_ a model's events are structured (e.g., event name, payload format).
3. **Service (`webhooks/service.py`):** A central function, `dispatch_webhook_event()`, which will be called from our views. This service looks up the model in the registry, gets its config, finds all subscribed endpoints, and enqueues the Huey tasks.

### Event triggering

We will **trigger webhook dispatches from the view layer** (i.e. DRF ViewSets) by calling the central `dispatch_webhook_event()` service. We will **NOT** put this logic in `models.save()`.

#### Rationale

This is a critical architectural decision.

1. **Solves data migrations:** Data migrations do _not_ go through the API view layer. By placing logic here, our migration scripts can freely update objects without dispatching possibly thousands of unwanted webhook events.
2. **Makes bulk operations explicit:** Since standard DRF views are singular, this naturally enforces our "1 event per 1 object" rule. If we build a custom bulk-create endpoint, we are _forced_ to explicitly loop and enqueue N tasks, making the cost visible.
3. **Decouples logic:** The model doesn't need to know about webhooks. The view's only job is to report "this just happened.". The central service handles the rest.

### Huey task execution

The `dispatch_webhook_event()` function will enqueue this Huey task. The task is responsible for the actual HTTP request and signature generation.

### Security & consumer management

- **Secret management**
  - **Decision:** We will support both auto-generated and user-provided secrets.
  - **Implementation:** The `WebhookEndpoint` DRF Serializer will treat the `secret` field as `write_only`.
  - On `create`, if the `secret` field is blank, the `save()` method will auto-generate one. The `create()` view response **MUST** include the newly generated secret so the user can copy it ("show once" behavior).
- **SSRF mitigation**
  - **Decision:** The MVP will use model-level validation.
  - **Implementation:** The `WebhookEndpoint.clean()` method will block URLs that resolve to internal, private, or loopback IP addresses.
  - **Rationale:** This is a critical baseline security measure for an MVP. It is not foolproof (e.g. DNS rebinding) and should be upgraded.
- **Event subscription**
  - **Decision:** Users must be able to select which events they subscribe to.
  - **Implementation:** The `event_types` `ManyToManyField` will link `WebhookEventType`s to endpoint objects. The UI will fetch a list of all available event types and render checkboxes for the user.

---

### Payload

The payload is the core data sent in the webhook. It will always be delivered in the HTTP POST request body.

The payload MUST be formatted as **JSON**, and the request will include a `Content-Type: application/json` header.

#### Payload structure

All webhook payloads from CISO Assistant adhere to the Standard Webhooks v1.0.0 specification, ensuring a consistent, top-level structure. This makes all payloads predictable and easy to parse.

The top-level JSON object will always contain

- **`type`** (string): The event type, formatted hierarchically with full stops. This identifies the action that occurred.
- **`timestamp`** (string): The [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) formatted timestamp of when the event occurred in our system (this is not the same as the `webhook-timestamp` header, which indicates when the send attempt was made).
- **`data`** (object): The object containing the event's data. Per our strategy, this will be a "thin" or "full" payload.

#### Payload strategy

CISO Assistant allows for two payload modes: **thin** and **full** payloads.

A "thin" payload contains _only the ID_ of the resource that changed, not the full object. You must use this ID to call back to our API to fetch the complete, up-to-date details.

**Example: `appliedcontrol.created` event**

```json
{
  "type": "appliedcontrol.created",
  "timestamp": "2025-11-13T14:35:06.123456Z",
  "data": {
    "id": "53709ff2-ade7-4172-9dee-daa580cbba5b"
  }
}
```

A "full" payload contains _the entirety_ of the resource that changed.

**Example: `appliedcontrol.created` event**

```json
{
  "type": "appliedcontrol.created",
  "timestamp": "2025-11-13T14:35:06.123456Z",
  "data": {
    "id": "53709ff2-ade7-4172-9dee-daa580cbba5b",
    "findings": [],
    "stakeholders": [],
    "cost": null,
    "path": [],
    "folder": {
      "str": "Global",
      "id": "5941b4a9-6a22-45bf-9044-38a5a4566696"
    },
    "reference_control": {
      "str": "DOC.AUDIT_PLAN - Audit plan document",
      "id": "988bd9d1-4381-4f26-b685-7ed0355d7560"
    },
    "priority": "P3",
    "category": "Process",
    "csf_function": "Govern",
    "evidences": [
      {
        "str": "acceptable_encryption_policy",
        "id": "5225715c-0291-409a-b176-99a613bd12b1"
      },
      {
        "str": "data_breach_response",
        "id": "c3af2b74-56ab-450f-9a79-41f5c47e53ac"
      }
    ],
    "objectives": [],
    "effort": null,
    "control_impact": null,
    "annual_cost": "0.00",
    "currency": "€",
    "annual_cost_display": "",
    "filtering_labels": [],
    "assets": [],
    "ranking_score": 0,
    "owner": [],
    "security_exceptions": [],
    "state": {
      "name": "incoming",
      "hexcolor": "#93c5fd"
    },
    "findings_count": 0,
    "is_assigned": false,
    "created_at": "2025-10-31T15:35:10.514059Z",
    "updated_at": "2025-11-21T17:19:17.819806Z",
    "name": "Audit plan document",
    "description": null,
    "ref_id": null,
    "status": "in_progress",
    "start_date": null,
    "eta": "2025-11-29",
    "expiry_date": null,
    "link": null,
    "progress_field": 100,
    "is_published": true,
    "observation": null,
    "sync_mappings": [
      {
        "id": "49eb13ee-f52d-45a9-82d8-ba0f21d1fb46",
        "remote_id": "KAN-1",
        "sync_status": "failed",
        "last_synced_at": "2025-11-06T13:02:23.269321Z",
        "last_sync_direction": "pull",
        "error_message": "Remote object was deleted",
        "provider": "jira"
      }
    ]
  }
}
```

---

### Webhook headers

All outgoing webhooks will include the following HTTP headers, as specified by Standard Webhooks v1.0.0. These headers are essential for verifying the payload's authenticity and ensuring idempotent processing.

- **`webhook-id`**: A unique identifier (e.g., `msg_...`) for this specific webhook message.
  - The consumer MUST use this ID as an **idempotency key** to prevent processing the same event more than once.
- **`webhook-timestamp`**: An integer unix timestamp (seconds since epoch) indicating when this specific send _attempt_ was made.
  - The consumer MUST check this timestamp to protect against replay attacks (e.g. by ensuring it's within a reasonable tolerance, like 5 minutes).
- **`webhook-signature`**: The HMAC signature used to verify the payload. For our MVP, this will always use the `v1` (HMAC-SHA256) scheme.

**Example headers:**

```http
webhook-id: msg_1a2b3c4d5e6f7a8b9c0d
webhook-timestamp: 1674087231
webhook-signature: v1,K5oZfzN95Z9UVu1EsfQmfVNQhnkZ2pj9o9NDN/H/pI4=
```

---

### Verifying signatures (MVP)

To ensure the webhook is from CISO Assistant and has not been tampered with, you **MUST** verify the `webhook-signature` before trusting the payload.

The content that we sign (the "signed content string") is created by concatenating the `webhook-id`, the `webhook-timestamp`, and the **raw JSON payload**, using a full-stop (`.`) as a delimiter.

Signed Content String Format:

`[webhook-id].[webhook-timestamp].[raw_request_body]`

Example Signed Content String:

```json
msg_1a2b3c4d5e6f7a8b9c0d.1674087231.{"type":"appliedcontrol.created","timestamp":"2025-11-13T14:35:06Z","data":{"id":"53709ff2-ade7-4172-9dee-daa580cbba5b"}}
```

**Verification steps:**

1. **Extract** the `webhook-id`, `webhook-timestamp`, and `webhook-signature` from the request headers
2. **Check Timestamp:** Verify that the `webhook-timestamp` is recent (e.g., within the last 5 minutes) to prevent replay attacks
3. **Create String:** Recreate the signed content string by concatenating the ID, the timestamp, and the **raw, unparsed** HTTP body
4. **Get Signature:** Parse the `webhook-signature` header. The `v1,` prefix indicates the HMAC-SHA256 scheme
5. **Calculate:** Compute your own expected HMAC-SHA256 signature using your shared `whsec_...` secret and the signed content string
6. **Compare:** **Securely compare** your expected signature with the received signature. You MUST use a constant-time comparison function to prevent timing attacks.

---

## MVP limitations & future iterations

- **No failure visibility (MVP):** The user has no UI to see failed webhooks. If Huey's 5 retries fail, the event is lost.
  - **Next:** Implement models to log every event, providing a UI for inspection and manual retries.
- **Basic SSRF protection (MVP):** URL validation is a good first step but not a complete solution.
  - **Next:** Implement a network-level egress proxy (e.g. [smokescreen](https://github.com/stripe/smokescreen)).
- **HMAC signatures only (MVP):**
  - **Next:** Add support for asymmetric (ed25519) signatures.
- **Decentralized triggers (MVP tradeoff):** The logic is cleanly decoupled but _not_ centralized. We must ensure that all code paths that modify data (e.g. management commands) also remember to call the `dispatch_webhook_event` service.
