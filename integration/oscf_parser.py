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


def process_ref_id(ref_id, truncate_to_three_parts=False):
    """
    Process a reference ID according to specified rules.

    Args:
        ref_id: The original reference ID
        truncate_to_three_parts: If True, truncate ref_id to three parts (a.b.c) if it has more parts

    Returns:
        Processed reference ID
    """
    if truncate_to_three_parts:
        parts = ref_id.split(".")
        if len(parts) > 3:
            return ".".join(parts[:3])

    return ref_id


def extract_compliance_data(oscf_file_path, framework, truncate_pci_refs=False):
    """
    Extract compliance data from OSCF file for a specific framework.

    Args:
        oscf_file_path: Path to the OSCF format JSON file
        framework: The compliance framework to extract (e.g., 'ISO27001')
        truncate_pci_refs: If True and framework is PCI-4.0, truncate ref_ids to three parts

    Returns:
        List of dictionaries containing ref_id and status_code
    """
    try:
        with open(oscf_file_path, "r") as file:
            data = json.load(file)

        results = []
        should_truncate = truncate_pci_refs and framework == "PCI-4.0"

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
                        # Process the reference ID if needed
                        processed_ref_id = process_ref_id(ref_id, should_truncate)

                        results.append(
                            {"ref_id": processed_ref_id, "status_code": status_code}
                        )

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
        "error": "not_applicable",
        # Add more mappings as needed
    }

    # Return the mapped value or a default
    return status_mapping.get(status_code.lower(), "not_applicable")


def send_kafka_messages(compliance_data, assessment_ref_id):
    """
    Send Kafka messages for each unique compliance data entry.

    Args:
        compliance_data: List of dictionaries with ref_id and status_code
        assessment_ref_id: The compliance assessment reference ID
    """
    # Create producer configuration
    conf = {"bootstrap.servers": BOOTSTRAP_SERVERS}

    # Create Producer instance
    producer = Producer(conf)

    # De-duplicate messages based on combination of ref_id and result
    unique_messages = {}
    for item in compliance_data:
        result = map_status_to_result(item["status_code"])

        # Create a unique key based on both ref_id and result
        key = f"{item['ref_id']}:{result}"

        # Store the unique combination
        unique_messages[key] = {"ref_id": item["ref_id"], "result": result}

    print(f"Connected to Kafka at {BOOTSTRAP_SERVERS}")
    print(
        f"Sending {len(unique_messages)} unique messages to topic {TOPIC} (reduced from {len(compliance_data)} total entries)"
    )

    for key, data in unique_messages.items():
        # Create message
        message = {
            "message_type": "update_requirement_assessment",
            "selector": {
                "compliance_assessment__ref_id": assessment_ref_id,
                "requirement__ref_id": data["ref_id"],
            },
            "values": {"result": data["result"]},
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
    parser.add_argument(
        "--truncate-pci-refs",
        action="store_true",
        help="For PCI-4.0 only: Truncate reference IDs to three parts (a.b.c)",
    )

    args = parser.parse_args()

    # Update global variables with command line arguments
    BOOTSTRAP_SERVERS = args.bootstrap_servers
    TOPIC = args.topic

    # Extract compliance data from OSCF file
    compliance_data = extract_compliance_data(
        args.oscf_file, args.framework, args.truncate_pci_refs
    )

    if not compliance_data:
        print(f"No compliance data found for framework '{args.framework}'")
        return

    print(
        f"Found {len(compliance_data)} compliance items for framework '{args.framework}'"
    )

    if args.dry_run:
        print("=== DRY RUN MODE (not sending to Kafka) ===")

        # De-duplicate messages based on combination of ref_id and result
        unique_messages = {}
        for item in compliance_data:
            result = map_status_to_result(item["status_code"])

            # Create a unique key based on both ref_id and result
            key = f"{item['ref_id']}:{result}"

            # Store the unique combination
            unique_messages[key] = {"ref_id": item["ref_id"], "result": result}

        # Print stats
        print(f"Found {len(compliance_data)} total compliance items")
        print(
            f"After de-duplication: {len(unique_messages)} unique messages will be sent"
        )

        # Count by result type
        result_counts = {}
        for data in unique_messages.values():
            result = data["result"]
            result_counts[result] = result_counts.get(result, 0) + 1

        # Print result distribution
        print("\nResult distribution:")
        for result, count in result_counts.items():
            print(f"  {result}: {count}")

        print("\nMessages that would be sent:")
        for data in unique_messages.values():
            message = {
                "message_type": "update_requirement_assessment",
                "selector": {
                    "compliance_assessment__ref_id": args.assessment_ref,
                    "requirement__ref_id": data["ref_id"],
                },
                "values": {"result": data["result"]},
            }
            print(f"Would send to topic '{TOPIC}':")
            print(json.dumps(message, indent=2))
            print("---")
    else:
        # Send Kafka messages
        send_kafka_messages(compliance_data, args.assessment_ref)


if __name__ == "__main__":
    main()
