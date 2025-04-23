# Event streaming in CISO Assistant

## CISO Assistant Kafka consumer specification

### Overview

The consumer is built for CISO Assistant and is responsible for processing messages that trigger successive API requests. Key features include:

- Avro Serialization with a Schema Registry to manage potential schema evolutions and maintain backward compatibility.
- Support for multiple use cases with clearly defined payload structures.
- Error handling via retries and a dead-letter queue (DLQ) strategy.

---

### Architecture & components

#### Components overview

- **Kafka Consumer**
  - **Platform:** Redpanda (Kafka-compatible)
  - **Subscription:** Topic `observation`
  - **Processing Model:** Single-message (no batching required for now)
- **Schema Registry**
  - **Purpose:** Store and manage Avro schemas.
  - **Usage:** Validate incoming messages and enforce non-breaking schema evolution through versioning.
- **API Client**
  - **Role:** Execute API calls based on message data.
  - **Authentication:** Handled at the consumer level (messages do not carry sensitive credentials).
- **Error Handling & Monitoring**
  - **Mechanism:** Retries with exponential backoff; DLQ for messages that exceed retry limits.
  - **Logging:** Detailed error logs and message metadata to aid troubleshooting.

#### Message flow

1. **Subscription & consumption:**  
   The consumer subscribes to the `observation` topic and listens continuously for new messages.
2. **Deserialization:**  
   Upon message receipt, the consumer retrieves the relevant Avro schema from the Schema Registry and deserializes the message payload.
3. **Message processing:**  
   Based on the `message_type` in the common envelope, the dispatcher routes the message to the corresponding processing logic.
4. **API request execution:**  
   The consumer makes authenticated API requests as defined by each use case.
5. **Error handling:**
   - **Transient Errors:** Retries with exponential backoff.
   - **Permanent Errors:** After a configurable number of retries, messages are forwarded to a DLQ for later analysis.
6. **Logging & monitoring:**  
   All processing activities and errors are logged, with metrics exposed for monitoring consumer health and DLQ size.

---

### Events and commands

We distinguish two types of messages in the event stream:

- **Events**: Messages that represent a state change or an observation (e.g., control status update, requirement assessment status update).
- **Commands**: Messages that request an action to be performed (e.g., create a new control, update a requirement assessment).

The fundamental difference between events and commands is that events are passive observations that represent something **that has already happened**, while commands are active requests for change. Thus, **commands may fail** and require proper error handling.

---

### Message schema

#### Common fields

The following fields are common to all commands:

- `message_type: string`: Use case to trigger (e.g. `update_applied_control_status`, `update_requirement_assessment_status`, `attach_evidence_to_applied_control`...)
- `version: int`: Schema version
- `selector: object`: Key-value pairs to pass to the API as filters (e.g. `{"ref_id": "ID.AM-01", "folder": "global/mydomain", "target": "single"}`)

#### Storing schema files

Schema files are stored as `.avsc` files in `dispatcher/redpanda/schemas/`.
Events are located in `dispatcher/redpanda/schemas/events/`, and commands in `dispatcher/redpanda/schemas/commands/`.

**Naming convention:** `<message_type>_v<schema_version>.avsc`.
<message_type> MUST be the same as the function name in the dispatcher service.
<schema_version> MUST be incremented for each schema change.

---

### Schema evolution & backwards compatibility

#### TBD

---

### Error handling, logging, and DLQ strategy

#### Error handling

- **Deserialization errors**

  - Log the error, including the message data and error message, then skip or forward the message as appropriate.

- **Processing errors**
  - **Transient issues:** Implement a retry mechanism with exponential backoff
  - **Persistent failures:** After reaching the maximum retry count (configurable), route the message to a Dead-Letter Queue (DLQ) for offline analysis and reprocessing.

#### Logging & monitoring

- **Logging**

  - Use structured logging, e.g. `structlog` python library to maintain consistency with the backend tech stack
  - Log key details for every processed message at the `INFO` level (e.g., `message_type`, `timestamp`).
  - Log error details, including stack traces

- **Monitoring**
  - Track consumer metrics such as processing latency, error rates, and DLQ volume.

---

### Configuration & deployment

#### Configuration

- **RedPanda**

  - Main topic name: `observation`

- **Schema registry**

  - TBD

- **Retry and DLQ settings**

  - Maximum retry count (default: `3`)
  - Exponential backoff parameters
    - Initial delay
  - DLQ topic name and retention policies

- **Consumer service**
  - Backend API URL (default: `localhost:8000/api`)
  - Backend API authentication credentials
