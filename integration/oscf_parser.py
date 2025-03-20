#!/usr/bin/env python3
import json
import os
import sys
import argparse
from confluent_kafka import Producer

# Configuration
BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")
TOPIC = "observation"
COMPLIANCE_ASSESSMENT_REF_ID = "ISO_001"  # Default value, can be overridden


def delivery_report(err, msg):
    """Callback function for message delivery reports."""
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        print(
            f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}"
        )


def extract_compliance_data(oscf_file_path, framework):
    try:
        with open(oscf_file_path, "r") as file:
            data = json.load(file)

        results = []

        # Process each node in the array
        for node in data:
            # Extract status code from the node
            status_code = node.get("status_code")

            # Check if node contains unmapped compliance data for the requested framework
            if "unmapped" in node and "compliance" in node["unmapped"]:
                if framework in node["unmapped"]["compliance"]:
                    # Extract reference IDs for the framework
                    ref_ids = node["unmapped"]["compliance"][framework]

                    # For each reference ID, create an entry with the status code
                    for ref_id in ref_ids:
                        results.append({"ref_id": ref_id, "status_code": status_code})

        return results

    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        print(f"Error processing OSCF file: {str(e)}")
        return []


def map_status_to_result(status_code):
    """
    Map the status code to a result value.

    Args:
        status_code: The status code from the OSCF file

    Returns:
        A result string (compliant, non_compliant, etc.)
    """
    # This mapping can be adjusted based on your specific requirements
    status_mapping = {
        "pass": "compliant",
        "fail": "non_compliant",
        "warning": "partially_compliant",
        # Add more mappings as needed
    }

    # Return the mapped value or a default
    return status_mapping.get(status_code.lower(), "not_assessed")


def send_kafka_messages(compliance_data, assessment_ref_id):
    # Create producer configuration
    conf = {"bootstrap.servers": BOOTSTRAP_SERVERS}

    # Create Producer instance
    producer = Producer(conf)

    print(f"Connected to Kafka at {BOOTSTRAP_SERVERS}")
    print(f"Sending {len(compliance_data)} messages to topic {TOPIC}")

    for item in compliance_data:
        # Create message
        message = {
            "message_type": "update_requirement_assessment",
            "selector": {
                "compliance_assessment__ref_id": assessment_ref_id,
                "requirement__ref_id": item["ref_id"],
            },
            "values": {"result": map_status_to_result(item["status_code"])},
        }

        # Produce the message
        producer.produce(
            topic=TOPIC,
            value=json.dumps(message).encode("utf-8"),
            callback=delivery_report,
        )

        # Trigger any events to be delivered
        producer.poll(0)

    # Wait for any outstanding messages to be delivered
    producer.flush()
    print("All messages sent successfully")


def main():
    global BOOTSTRAP_SERVERS, TOPIC

    parser = argparse.ArgumentParser(
        description="Parse OSCF file and send compliance data to Kafka"
    )
    parser.add_argument("oscf_file", help="Path to the OSCF format JSON file")
    parser.add_argument(
        "framework", help="Compliance framework to extract (e.g., ISO27001)"
    )
    parser.add_argument(
        "--assessment-ref",
        help="Compliance assessment reference ID",
        default=COMPLIANCE_ASSESSMENT_REF_ID,
    )
    parser.add_argument(
        "--bootstrap-servers", help="Kafka bootstrap servers", default=BOOTSTRAP_SERVERS
    )
    parser.add_argument("--topic", help="Kafka topic", default=TOPIC)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process file and show messages without sending to Kafka",
    )

    args = parser.parse_args()

    # Update global variables with command line arguments
    BOOTSTRAP_SERVERS = args.bootstrap_servers
    TOPIC = args.topic

    # Extract compliance data from OSCF file
    compliance_data = extract_compliance_data(args.oscf_file, args.framework)

    if not compliance_data:
        print(f"No compliance data found for framework '{args.framework}'")
        return

    print(
        f"Found {len(compliance_data)} compliance items for framework '{args.framework}'"
    )

    if args.dry_run:
        print("=== DRY RUN MODE (not sending to Kafka) ===")
        for item in compliance_data:
            message = {
                "message_type": "update_requirement_assessment",
                "selector": {
                    "compliance_assessment__ref_id": args.assessment_ref,
                    "requirement__ref_id": item["ref_id"],
                },
                "values": {"result": map_status_to_result(item["status_code"])},
            }
            print(f"Would send to topic '{TOPIC}':")
            print(json.dumps(message, indent=2))
            print("---")
    else:
        # Send Kafka messages
        send_kafka_messages(compliance_data, args.assessment_ref)


if __name__ == "__main__":
    main()
