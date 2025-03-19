import io
import requests
import avro.schema
import avro.io

# Configuration for the schema registry URL (adjust as needed)
SCHEMA_REGISTRY_URL = "http://localhost:18081"


def fetch_schema_from_registry(
    schema_id: int, registry_url: str = SCHEMA_REGISTRY_URL
) -> avro.schema.Schema:
    """
    Fetches and parses the Avro schema corresponding to the given schema_id from the Redpanda Schema Registry.

    Args:
        schema_id (int): The schema identifier extracted from the message.
        registry_url (str): URL of the schema registry.

    Returns:
        avro.schema.Schema: The parsed Avro schema.
    """
    url = f"{registry_url}/schemas/ids/{schema_id}"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch schema for id {schema_id}: {response.text}")

    schema_json = response.json().get("schema")
    if not schema_json:
        raise Exception("Schema not found in registry response.")

    return avro.schema.Parse(schema_json)


def deserialize_avro_message(
    message_bytes: bytes, registry_url: str = SCHEMA_REGISTRY_URL
) -> object:
    """
    Deserializes an Avro-encoded message using its schema from the schema registry.

    The message is expected to follow the Confluent wire format:
      - 1 byte: magic byte (0)
      - 4 bytes: schema ID (big endian)
      - remaining bytes: Avro serialized payload

    Args:
        message_bytes (bytes): The raw message bytes.
        registry_url (str): URL of the schema registry.

    Returns:
        dict: The deserialized Avro record.
    """
    if len(message_bytes) < 5:
        raise Exception("Message too short to contain schema information.")

    # Validate magic byte (should be 0)
    magic_byte = message_bytes[0]
    if magic_byte != 0:
        raise Exception(f"Invalid magic byte: {magic_byte}")

    # Extract the schema id (next 4 bytes)
    schema_id = int.from_bytes(message_bytes[1:5], byteorder="big")

    # Fetch the corresponding schema from the registry
    schema = fetch_schema_from_registry(schema_id, registry_url)

    # Deserialize the remaining payload using the retrieved schema
    bytes_reader = io.BytesIO(message_bytes[5:])
    decoder = avro.io.BinaryDecoder(bytes_reader)
    reader = avro.io.DatumReader(schema)
    decoded_record = reader.read(decoder)

    return decoded_record


# Example usage:
if __name__ == "__main__":
    # Assume we have a raw message from Redpanda
    # (This is just an example. In production, you'll get the actual message bytes.)
    with open("sample_avro_message.bin", "rb") as f:
        raw_message = f.read()

    try:
        record = deserialize_avro_message(raw_message)
        print("Deserialized record:", record)
    except Exception as e:
        print("Failed to deserialize message:", e)
