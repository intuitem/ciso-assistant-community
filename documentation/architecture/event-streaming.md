# Event streaming in CISO Assistant

## CISO Assistant Kafka consumer specification

### Overview

The consumer is built for CISO Assistant and is responsible for processing events that trigger successive API requests. Key features include:

- Avro Serialization with a Schema Registry to manage potential schema evolutions and maintain backward compatibility.
- Support for multiple use cases with clearly defined payload structures.
- Error handling via retries and a dead-letter queue (DLQ) strategy.

---

### Architecture & components

#### Components overview

- **Kafka Consumer**
  - **Platform:** Redpanda (Kafka-compatible)
  - **Subscription:** Topic `observation`
  - **Processing Model:** Single-event (no batching required for now)
- **Schema Registry**
  - **Purpose:** Store and manage Avro schemas.
  - **Usage:** Validate incoming messages and enforce non-breaking schema evolution through versioning.
- **API Client**
  - **Role:** Execute API calls based on event data.
  - **Authentication:** Handled at the consumer level (events do not carry sensitive credentials).
- **Error Handling & Monitoring**
  - **Mechanism:** Retries with exponential backoff; DLQ for events that exceed retry limits.
  - **Logging:** Detailed error logs and event metadata to aid troubleshooting.

#### Message flow

1. **Subscription & consumption:**  
   The consumer subscribes to the `observation` topic and listens continuously for new messages.
2. **Deserialization:**  
   Upon message receipt, the consumer retrieves the relevant Avro schema from the Schema Registry and deserializes the event payload.
3. **Event processing:**  
   Based on the `event_type` in the common envelope, the consumer routes the event to the corresponding processing logic.
4. **API request execution:**  
   The consumer makes authenticated API requests as defined by each use case.
5. **Error handling:**
   - **Transient Errors:** Retries with exponential backoff.
   - **Permanent Errors:** After a configurable number of retries, events are forwarded to a DLQ for later analysis.
6. **Logging & monitoring:**  
   All processing activities and errors are logged, with metrics exposed for monitoring consumer health and DLQ size.

---

### Event schema

#### Common fields

The following fields are common to all events:

- `event_id: UUID4`: Unique identifier for the event
- `event_type: string`: Use case to trigger (e.g. `update_applied_control_status`, `update_requirement_assessment_status`, `attach_evidence_to_applied_control`...)
- `version: int`: Schema version

---

### Schema evolution & backwards compatibility

#### TBD

---

### Error handling, logging, and DLQ strategy

#### Error handling

- **Deserialization errors**

  - Log the error, including the event data and error message, then skip or forward the event as appropriate.

- **Processing errors**
  - **Transient issues:** Implement a retry mechanism with exponential backoff
  - **Persistent failures:** After reaching the maximum retry count (configurable), route the event to a Dead-Letter Queue (DLQ) for offline analysis and reprocessing.

#### Logging & monitoring

- **Logging**

  - Use structured logging, e.g. `structlog` python library to maintain consistency with the backend tech stack
  - Log key details for every processed event at the `INFO` level (e.g., `event_id`, `event_type`, `timestamp`).
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
