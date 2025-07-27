import yaml
import json
from genson import SchemaBuilder

with open("values.yaml", "r") as f:
    data = yaml.safe_load(f)

builder = SchemaBuilder()
builder.add_object(data)
schema = builder.to_schema()

# Set JSON Schema version
schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"

with open("values.schema.json", "w") as f:
    json.dump(schema, f, indent=4)
