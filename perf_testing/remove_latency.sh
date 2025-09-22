#!/bin/bash
echo "Removing database latency..."
curl -X DELETE http://localhost:8474/proxies/postgres/toxics/latency \
  -w "\nHTTP Status: %{http_code}\n"

echo "✅ Database latency removed"
