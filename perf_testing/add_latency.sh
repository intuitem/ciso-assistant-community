#!/bin/bash
LATENCY=${1:-10} # Default 10ms if no argument provided

echo "Adding ${LATENCY}ms latency to database..."
curl -X POST http://localhost:8474/proxies/postgres/toxics \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"latency\",
    \"type\": \"latency\",
    \"attributes\": {\"latency\": $LATENCY}
  }" \
  -w "\nHTTP Status: %{http_code}\n"

echo "✅ Database latency set to ${LATENCY}ms"
