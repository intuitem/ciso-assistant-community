#!/bin/bash
echo "Current toxics on postgres proxy:"
curl -s http://localhost:8474/proxies/postgres/toxics | jq '.' || curl -s http://localhost:8474/proxies/postgres/toxics
