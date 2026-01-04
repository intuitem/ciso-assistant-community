#!/usr/bin/env python3
import json
import os
from confluent_kafka import Producer

# Configuration
BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")
TOPIC = "observation"

# The message to send
MESSAGE = {
    "message_type": "update_requirement_assessment",
    "selector": {
        "compliance_assessment__ref_id": "ISO_001",
        "requirement__ref_id": "A.5.1",
    },
    "values": {"result": "compliant"},
}


def delivery_report(err, msg):
    """Callback function for message delivery reports."""
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        print(
            f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}"
        )


def send_kafka_message():
    # Create producer configuration
    conf = {"bootstrap.servers": BOOTSTRAP_SERVERS}

    # Create Producer instance
    producer = Producer(conf)

    print(f"Connected to Kafka at {BOOTSTRAP_SERVERS}")
    print(f"Sending message to topic {TOPIC}:")
    print(json.dumps(MESSAGE, indent=2))

    # Produce the message
    producer.produce(
        topic=TOPIC, value=json.dumps(MESSAGE).encode("utf-8"), callback=delivery_report
    )

    # Wait for any outstanding messages to be delivered
    producer.flush()
    print("Message sent successfully")


if __name__ == "__main__":
    send_kafka_message()
