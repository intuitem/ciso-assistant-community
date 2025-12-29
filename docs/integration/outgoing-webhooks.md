# Outgoing webhooks

## Outgoing Webhooks

Webhooks allow CISO Assistant to notify external systems in real-time when specific events occur within your GRC platform. Instead of polling our API every few minutes to check for changes, we will push data to you as soon as it happens.

### When to use Webhooks

Webhooks are ideal for building automation pipelines and keeping external systems in sync. Common use cases include:

* **ChatOps:** Notify a Slack or Teams channel when a new Risk is identified.
* **Ticket Sync:** Automatically create a Jira ticket when an `AppliedControl` fails validation.
* **Audit Logging:** Archive all `deleted` events to an external immutable storage bucket for compliance evidence.
* **CI/CD Gates:** Trigger a build pipeline scan when a specific policy is updated.

***

### Supported Events

You can subscribe to events at a granular level. Currently, CISO Assistant supports the following events:

* Applied controls:
  * `appliedcontrol.created`
  * `appliedcontrol.updated`
  * `appliedcontrol.deleted`
* Assets:
  * `asset.created`
  * `asset.updated`
  * `asset.deleted`

***

### Configuration & Security Features

CISO Assistant adheres to the [Standard Webhooks v1.0.0](https://www.standardwebhooks.com/) [specification](https://github.com/standard-webhooks/standard-webhooks/blob/main/spec/standard-webhooks.md). We prioritize security to ensure that the data sent to your systems is authentic and has not been tampered with.

#### 1. Payload Strategies: Full vs. Thin

When configuring an endpoint, you can choose between two payload strategies.

* Thin Payloads (<mark style="color:purple;">PRO</mark>) (Recommended for Security):
  * What it sends: Only the `id` of the changed resource.
  * How to process: Your system receives the ID, then makes an authenticated API call back to CISO Assistant to fetch the details.
  * Why choose this: This is the most secure method. It ensures that the receiving system has the correct permissions to view the data and guarantees you are always processing the latest version of the object.
* Full Payloads (Recommended for Simplicity):
  * What it sends: The complete JSON representation of the object at the time of the event.
  * How to process: Use the data directly from the POST body.
  * Why choose this: Reduces integration effort by removing the need for a callback API request. Ideal for simple notifications (e.g., Slack alerts).

#### 2. Secret Keys & Signatures

When you create a webhook endpoint, you can generate a unique secret key (`whsec_...`). You will only be shown this secret once.

Every request we send to you is signed using this secret (via HMAC-SHA256). By verifying this signature, you ensure:

1. Authenticity: The message definitely came from CISO Assistant.
2. Integrity: The message content was not altered in transit.

#### 3. Replay Protection (Timestamps)

Attackers may try to intercept a valid webhook request and "replay" it later to trick your system (e.g., triggering a deployment twice).

To prevent this, we include a timestamp in the signature. Your application should reject any request that is older than your tolerance window (e.g., 5 minutes).

#### 4. Idempotency (IDs)

Network issues may cause us to retry sending a webhook, resulting in your server receiving the same message twice. Every webhook includes a unique `webhook-id`. You should log these IDs and ensure you do not process the same ID more than once.

***

### The Integration Journey

1.  Enable the Webhooks feature flag in Settings > Feature flags<br>

    <figure><img src="../.gitbook/assets/image (62).png" alt=""><figcaption></figcaption></figure>
2.  Create an Endpoint: In the CISO Assistant UI, navigate to Settings > Webhooks.<br>

    <figure><img src="../.gitbook/assets/image (63).png" alt=""><figcaption></figcaption></figure>
3. Configure: Enter your receiver URL and select the events you want to listen to (e.g., `appliedcontrol.updated`).
4. Select Payload Type: Choose "Full" or "Thin" based on your security requirements.
5.  Save & Copy Secret: Copy the `whsec_...` secret immediately. You will need this for your consumer.<br>

    <figure><img src="../.gitbook/assets/image (64).png" alt=""><figcaption></figcaption></figure>
6. Develop: Write your consumer code (see examples below).

***

### Technical Reference

#### Payload Structure

All payloads follow the Standard Webhooks JSON structure.

Top-Level Fields:

* `type`: The event name (e.g., `appliedcontrol.created`).
* `timestamp`: When the event happened (ISO 8601).
* `data`: The payload data (varies by "Thin" or "Full").

**Example: Thin Payload**

```json
{
  "type": "appliedcontrol.created",
  "timestamp": "2025-11-13T14:35:06Z",
  "data": {
    "id": "53709ff2-ade7-4172-9dee-daa580cbba5b"
  }
}
```

**Example: Full Payload**

```json
{
  "type": "appliedcontrol.created",
  "timestamp": "2025-11-13T14:35:06Z",
  "data": {
    "id": "53709ff2-ade7-4172-9dee-daa580cbba5b",
    "name": "MFA Enforcement",
    "status": "active",
    "owner": "john.doe@example.com",
    ...
  }
}
```

#### Headers

We send the following headers with every request:

* `Content-Type`: `application/json`
* `webhook-id`: Unique message ID (for idempotency).
* `webhook-timestamp`: Unix timestamp of the send attempt.
* `webhook-signature`: The signature string, e.g., `v1,BmX...`

***

### Verifying the Signature

You MUST verify the signature to ensure security. Do not trust the payload content until verification passes.

The Algorithm:

1. Extract the `webhook-id`, `webhook-timestamp`, and `webhook-signature`.
2. Concatenate strings to form the signed content: `[webhook-id].[webhook-timestamp].[raw_body]`.
3. Calculate the HMAC-SHA256 of this string using your `whsec_...` secret.
4. Compare your calculated signature with the one provided in the header.

Python Example (Django/FastAPI/Flask)

```python
import hmac
import hashlib
import base64
import time

def verify_webhook(request, secret):
    # 1. Get Headers
    msg_id = request.headers.get("webhook-id")
    msg_timestamp = request.headers.get("webhook-timestamp")
    signature_header = request.headers.get("webhook-signature")
    
    if not (msg_id and msg_timestamp and signature_header):
        raise ValueError("Missing webhook headers")

    # 2. Verify Timestamp (Replay Protection)
    # Reject if older than 5 minutes
    now = int(time.time())
    if now - int(msg_timestamp) > 300:
        raise ValueError("Message timestamp too old")

    # 3. Construct Signed Content
    # IMPORTANT: Use the raw bytes of the request body
    body = request.body.decode("utf-8") 
    to_sign = f"{msg_id}.{msg_timestamp}.{body}"

    # 4. Calculate Expected Signature
    # The header format is "v1,signature_hash"
    # We only support v1 (HMAC-SHA256) for now
    secret_bytes = secret.encode("utf-8")
    to_sign_bytes = to_sign.encode("utf-8")
    
    digest = hmac.new(secret_bytes, to_sign_bytes, hashlib.sha256).digest()
    calculated_signature = base64.b64encode(digest).decode()

    # 5. Compare Securely
    # Extract the hash from "v1,..."
    provided_signature = signature_header.split(",")[1]
    
    if not hmac.compare_digest(calculated_signature, provided_signature):
        raise ValueError("Invalid signature")

    return True
```

***

### Operational Details

#### Retries & Reliability

We use a "best effort" delivery system.

* **Success:** We consider a delivery successful if your server returns any `2xx` HTTP status code (e.g., `200 OK`, `201 Created`).
* **Failure:** Any other status code (`400`, `401`, `500`) or a connection timeout is considered a failure.
* **Retry Schedule:** If delivery fails, we will retry approximately 5 times over a 15-minute window with exponential backoff.
* **Message Loss:** If the endpoint is still unreachable after the final retry, the message is discarded. We currently do not provide a UI to replay failed messages manually.

#### IP Allowlisting (Compensatory Controls)

If your receiving endpoint is behind a corporate firewall, you may need to allowlist the IP address of the CISO Assistant server.

* SaaS Users: ???
* On-Prem Users: The webhooks originate from the IP address of the server running the `huey` worker process. Ensure your firewall allows inbound HTTPS traffic from this internal or external IP.
