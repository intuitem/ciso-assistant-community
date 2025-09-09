#!/bin/bash

echo "Setting up Toxiproxy..."

# Check if Toxiproxy is running
if ! curl -s http://localhost:8474/version >/dev/null; then
  echo "❌ Toxiproxy is not running. Start with: docker compose up -d"
  exit 1
fi

# Remove proxy if it exists (cleanup)
curl -s -X DELETE http://localhost:8474/proxies/postgres >/dev/null

# Create the PostgreSQL proxy
echo "Creating postgres proxy..."
response=$(curl -s -X POST http://localhost:8474/proxies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "postgres",
    "listen": "0.0.0.0:5433",
    "upstream": "postgres:5432"
  }')

if echo "$response" | grep -q "postgres"; then
  echo "✅ Postgres proxy created successfully"
  echo "   Listening on: localhost:5433"
  echo "   Forwarding to: postgres:5432"
else
  echo "❌ Failed to create proxy: $response"
  exit 1
fi

# List all proxies to verify
echo ""
echo "Current proxies:"
curl -s http://localhost:8474/proxies | jq '.' || curl -s http://localhost:8474/proxies
